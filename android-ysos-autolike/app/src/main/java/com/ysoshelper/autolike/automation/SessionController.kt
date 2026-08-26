package com.ysoshelper.autolike.automation

import com.ysoshelper.autolike.accessibility.NodeRef
import com.ysoshelper.autolike.accessibility.UiSnapshot
import com.ysoshelper.autolike.matching.LikeMatch
import com.ysoshelper.autolike.matching.ProfileIdentity
import com.ysoshelper.autolike.matching.SafetyDecision
import com.ysoshelper.autolike.matching.SafetyGuard
import com.ysoshelper.autolike.matching.YsosUiMatcher
import com.ysoshelper.autolike.matching.toSanitizedDiagnostics
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

interface ActionExecutor {
    suspend fun click(target: NodeRef): Boolean
}

interface DelayProvider {
    suspend fun delayMs(ms: Long)
}

interface RandomDelay {
    fun nextDelayMs(minMs: Long, maxMs: Long): Long
}

class SessionController(
    private val matcher: YsosUiMatcher,
    private val identity: ProfileIdentity,
    private val safetyGuard: SafetyGuard,
    private val actionExecutor: ActionExecutor,
    private val delayProvider: DelayProvider,
    private val randomDelay: RandomDelay,
    private val nowMs: () -> Long,
    private val scope: CoroutineScope,
    private val log: SessionLog = SessionLog(),
) : AutomationPort {
    private val _status = MutableStateFlow(SessionStatus())
    override val status: StateFlow<SessionStatus> = _status.asStateFlow()

    private val pipelineMutex = Mutex()
    private var processingJob: Job? = null
    private var config: SessionConfig? = null
    private var latestSnapshot: UiSnapshot? = null
    private var lastHandledFingerprint: String? = null
    private var dryRunHandledFingerprint: String? = null
    private var unresolvedCount = 0

    override fun startSession(config: SessionConfig): ConfigValidation {
        val validation = config.validate()
        if (validation is ConfigValidation.Invalid) {
            _status.value = _status.value.copy(phase = SessionPhase.ERROR, lastMessage = validation.message)
            return validation
        }
        processingJob?.cancel()
        this.config = config
        latestSnapshot = null
        lastHandledFingerprint = null
        dryRunHandledFingerprint = null
        unresolvedCount = 0
        log.clear()
        _status.value = SessionStatus(
            phase = SessionPhase.ARMED,
            realLikes = 0,
            dryRunProcessed = 0,
            limit = config.limit,
            lastMessage = "Waiting for YSOS",
        )
        return ConfigValidation.Valid
    }

    override fun stopSession(reason: String) {
        processingJob?.cancel()
        processingJob = null
        val old = _status.value
        _status.value = old.copy(phase = SessionPhase.STOPPED, lastMessage = reason)
        log.append(LogEntry(nowMs(), SessionPhase.STOPPED, null, LogAction.STOP, reason, old.realLikes, old.limit))
    }

    fun submitSnapshot(snapshot: UiSnapshot) {
        val current = _status.value
        if (current.phase in setOf(SessionPhase.STOPPED, SessionPhase.COMPLETED, SessionPhase.ERROR)) return
        latestSnapshot = snapshot

        if (snapshot.packageName != YSOS_PACKAGE) {
            processingJob?.cancel()
            processingJob = null
            _status.value = current.copy(phase = SessionPhase.ARMED, lastMessage = "Waiting for YSOS")
            return
        }

        when (val safety = safetyGuard.inspect(snapshot)) {
            SafetyDecision.Safe -> Unit
            is SafetyDecision.Stop -> {
                processingJob?.cancel()
                processingJob = null
                fail(safety.reason)
                return
            }
        }

        if (processingJob?.isActive == true) return
        processingJob = scope.launch {
            try {
                pipelineMutex.withLock { processSnapshot(snapshot) }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (t: Throwable) {
                fail("Unhandled automation error: ${t.message ?: t::class.java.simpleName}")
            }
        }
    }

    private suspend fun processSnapshot(initial: UiSnapshot) {
        val cfg = config ?: return
        if (_status.value.realLikes >= cfg.limit) {
            complete()
            return
        }

        val initialMatch = when (val match = matcher.resolveLike(initial)) {
            LikeMatch.None -> {
                unresolvedCount += 1
                if (unresolvedCount >= 3) fail("Like control could not be resolved")
                else _status.value = _status.value.copy(
                    phase = SessionPhase.WAITING_FOR_PROFILE,
                    lastMessage = "Waiting for a resolvable profile",
                )
                return
            }
            is LikeMatch.Ambiguous -> {
                fail("Like control is ambiguous")
                return
            }
            is LikeMatch.Unique -> match
        }
        unresolvedCount = 0
        val fingerprint = identity.fingerprint(initial, initialMatch.target)
        if (fingerprint == lastHandledFingerprint || fingerprint == dryRunHandledFingerprint) {
            _status.value = _status.value.copy(
                phase = SessionPhase.WAITING_FOR_NEXT_PROFILE,
                lastMessage = "Waiting for next profile",
            )
            return
        }

        val waitMs = randomDelay.nextDelayMs(cfg.minDelayMs, cfg.maxDelayMs)
        _status.value = _status.value.copy(
            phase = SessionPhase.DELAYING,
            lastMessage = "Waiting ${waitMs / 1000.0}s before revalidation",
        )
        delayProvider.delayMs(waitMs)

        _status.value = _status.value.copy(phase = SessionPhase.REVALIDATING, lastMessage = "Revalidating profile")
        val latest = latestSnapshot ?: return
        if (latest.packageName != YSOS_PACKAGE) {
            _status.value = _status.value.copy(phase = SessionPhase.ARMED, lastMessage = "Waiting for YSOS")
            return
        }
        when (val safety = safetyGuard.inspect(latest)) {
            SafetyDecision.Safe -> Unit
            is SafetyDecision.Stop -> {
                fail(safety.reason)
                return
            }
        }
        val latestMatch = when (val match = matcher.resolveLike(latest)) {
            is LikeMatch.Unique -> match
            LikeMatch.None -> {
                _status.value = _status.value.copy(phase = SessionPhase.WAITING_FOR_PROFILE, lastMessage = "Like control changed")
                return
            }
            is LikeMatch.Ambiguous -> {
                fail("Like control became ambiguous")
                return
            }
        }
        val latestFingerprint = identity.fingerprint(latest, latestMatch.target)
        if (latestFingerprint != fingerprint) {
            _status.value = _status.value.copy(phase = SessionPhase.WAITING_FOR_PROFILE, lastMessage = "Profile changed during delay")
            return
        }

        if (cfg.dryRun) {
            dryRunHandledFingerprint = fingerprint
            val next = _status.value.dryRunProcessed + 1
            _status.value = _status.value.copy(
                phase = SessionPhase.DRY_RUN,
                dryRunProcessed = next,
                lastMessage = "WOULD_LIKE — manually advance to a new profile",
            )
            log.append(LogEntry(nowMs(), SessionPhase.DRY_RUN, fingerprint, LogAction.WOULD_LIKE, "Dry Run", next, cfg.limit))
            return
        }

        _status.value = _status.value.copy(phase = SessionPhase.ACTING, lastMessage = "Liking current profile")
        val clicked = actionExecutor.click(latestMatch.target)
        if (!clicked) {
            _status.value = _status.value.copy(phase = SessionPhase.WAITING_FOR_PROFILE, lastMessage = "Like click was rejected by Android")
            log.append(LogEntry(nowMs(), SessionPhase.WAITING_FOR_PROFILE, fingerprint, LogAction.NO_ACTION, "ACTION_CLICK returned false", _status.value.realLikes, cfg.limit))
            return
        }

        lastHandledFingerprint = fingerprint
        val count = _status.value.realLikes + 1
        log.append(LogEntry(nowMs(), SessionPhase.ACTING, fingerprint, LogAction.LIKE, "ACTION_CLICK succeeded", count, cfg.limit))
        if (count >= cfg.limit) {
            _status.value = _status.value.copy(realLikes = count)
            complete()
        } else {
            _status.value = _status.value.copy(
                phase = SessionPhase.WAITING_FOR_NEXT_PROFILE,
                realLikes = count,
                lastMessage = "Like $count/${cfg.limit} — waiting for next profile",
            )
        }
    }

    private fun complete() {
        val old = _status.value
        _status.value = old.copy(phase = SessionPhase.COMPLETED, lastMessage = "Session completed at ${old.realLikes}/${old.limit}")
    }

    private fun fail(reason: String) {
        processingJob?.cancel()
        processingJob = null
        val old = _status.value
        _status.value = old.copy(phase = SessionPhase.ERROR, lastMessage = reason)
        log.append(LogEntry(nowMs(), SessionPhase.ERROR, null, LogAction.ERROR, reason, old.realLikes, old.limit))
    }

    override fun diagnosticsText(): String = latestSnapshot?.toSanitizedDiagnostics()
        ?: "No YSOS accessibility snapshot available"

    override fun sessionLogText(): String = log.asText()
}
