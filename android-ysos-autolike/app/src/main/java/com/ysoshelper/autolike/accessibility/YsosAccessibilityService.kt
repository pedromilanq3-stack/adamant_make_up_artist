package com.ysoshelper.autolike.accessibility

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent
import com.ysoshelper.autolike.YsosAutoLikeApplication
import com.ysoshelper.autolike.automation.AutomationPort
import com.ysoshelper.autolike.automation.ConfigValidation
import com.ysoshelper.autolike.automation.SessionConfig
import com.ysoshelper.autolike.automation.SessionController
import com.ysoshelper.autolike.automation.SessionStatus
import com.ysoshelper.autolike.automation.YSOS_PACKAGE
import com.ysoshelper.autolike.matching.ProfileIdentity
import com.ysoshelper.autolike.matching.SafetyGuard
import com.ysoshelper.autolike.matching.YsosUiMatcher
import com.ysoshelper.autolike.matching.toSanitizedDiagnostics
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class YsosAccessibilityService : AccessibilityService(), AutomationPort {
    private val mapper = AccessibilityTreeMapper()
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private lateinit var controller: SessionController
    private lateinit var app: YsosAutoLikeApplication
    private val _status = MutableStateFlow(SessionStatus())
    override val status: StateFlow<SessionStatus> = _status.asStateFlow()
    private var latestSnapshot: UiSnapshot? = null

    override fun onServiceConnected() {
        super.onServiceConnected()
        app = application as YsosAutoLikeApplication
        controller = SessionController(
            matcher = YsosUiMatcher(),
            identity = ProfileIdentity(),
            safetyGuard = SafetyGuard(),
            actionExecutor = AndroidActionExecutor { rootInActiveWindow },
            delayProvider = CoroutineDelayProvider(),
            randomDelay = KotlinRandomDelay(),
            nowMs = System::currentTimeMillis,
            scope = serviceScope,
        )
        serviceScope.launch { controller.status.collect { _status.value = it } }
        app.container.serviceBridge.register(this)
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (!::controller.isInitialized) return
        val packageName = event?.packageName?.toString() ?: return
        if (packageName != YSOS_PACKAGE) {
            controller.submitSnapshot(UiSnapshot(packageName, emptyList(), System.currentTimeMillis()))
            return
        }
        val root = rootInActiveWindow ?: return
        val snapshot = mapper.map(root, packageName, System.currentTimeMillis())
        latestSnapshot = snapshot
        controller.submitSnapshot(snapshot)
    }

    override fun onInterrupt() {
        if (::controller.isInitialized) controller.stopSession("Accessibility service interrupted")
    }

    override fun onDestroy() {
        if (::controller.isInitialized) controller.stopSession("Accessibility service stopped")
        if (::app.isInitialized) app.container.serviceBridge.unregister(this)
        serviceScope.cancel()
        super.onDestroy()
    }

    override fun startSession(config: SessionConfig): ConfigValidation =
        if (::controller.isInitialized) controller.startSession(config)
        else ConfigValidation.Invalid("Accessibility service is not ready")

    override fun stopSession(reason: String) {
        if (::controller.isInitialized) controller.stopSession(reason)
    }

    override fun diagnosticsText(): String = latestSnapshot?.toSanitizedDiagnostics()
        ?: "No YSOS accessibility snapshot available"

    override fun sessionLogText(): String =
        if (::controller.isInitialized) controller.sessionLogText() else "No session log available"
}
