package com.ysoshelper.autolike.automation

import com.ysoshelper.autolike.accessibility.NodeRef
import com.ysoshelper.autolike.accessibility.UiNode
import com.ysoshelper.autolike.accessibility.UiSnapshot
import com.ysoshelper.autolike.matching.ProfileIdentity
import com.ysoshelper.autolike.matching.SafetyGuard
import com.ysoshelper.autolike.matching.YsosUiMatcher
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceUntilIdle
import org.junit.Assert.assertEquals
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class SessionControllerTest {
    private class FakeActionExecutor(var result: Boolean = true) : ActionExecutor {
        val clicks = mutableListOf<NodeRef>()
        override suspend fun click(target: NodeRef): Boolean { clicks += target; return result }
    }
    private class ImmediateDelay : DelayProvider {
        val delays = mutableListOf<Long>()
        override suspend fun delayMs(ms: Long) { delays += ms }
    }
    private class FixedRandomDelay(private val value: Long) : RandomDelay {
        override fun nextDelayMs(minMs: Long, maxMs: Long) = value
    }

    private fun snapshot(name: String, packageName: String = YSOS_PACKAGE, extraLike: Boolean = false): UiSnapshot {
        val nodes = mutableListOf(
            UiNode(NodeRef(listOf(0), null, null, name), "TextView", null, null, name, false, true, false, "x"),
            UiNode(NodeRef(listOf(1), null, "Curtir", null), "Button", null, "Curtir", null, true, true, false, "y"),
        )
        if (extraLike) nodes += UiNode(NodeRef(listOf(2), null, "Like", null), "Button", null, "Like", null, true, true, false, "z")
        return UiSnapshot(packageName, nodes, 0)
    }

    private data class Fixture(val scope: TestScope, val executor: FakeActionExecutor, val delay: ImmediateDelay, val controller: SessionController)
    private fun fixture(clickResult: Boolean = true): Fixture {
        val dispatcher = StandardTestDispatcher()
        val scope = TestScope(dispatcher)
        val executor = FakeActionExecutor(clickResult)
        val delay = ImmediateDelay()
        val controller = SessionController(YsosUiMatcher(), ProfileIdentity(), SafetyGuard(), executor, delay, FixedRandomDelay(3_000), { 1L }, scope)
        return Fixture(scope, executor, delay, controller)
    }

    @Test fun limit_is_enforced_at_exactly_n_successful_clicks() {
        val f = fixture(); f.controller.startSession(SessionConfig.defaults().copy(limit = 3, dryRun = false))
        listOf("A", "B", "C", "D").forEach { f.controller.submitSnapshot(snapshot(it)); f.scope.advanceUntilIdle() }
        assertEquals(3, f.executor.clicks.size)
        assertEquals(SessionPhase.COMPLETED, f.controller.status.value.phase)
    }

    @Test fun failed_click_does_not_increment_count() {
        val f = fixture(false); f.controller.startSession(SessionConfig.defaults().copy(limit = 1, dryRun = false))
        f.controller.submitSnapshot(snapshot("A")); f.scope.advanceUntilIdle()
        assertEquals(0, f.controller.status.value.realLikes)
    }

    @Test fun duplicate_fingerprint_is_not_clicked_twice() {
        val f = fixture(); f.controller.startSession(SessionConfig.defaults().copy(limit = 2, dryRun = false))
        f.controller.submitSnapshot(snapshot("A")); f.scope.advanceUntilIdle(); f.controller.submitSnapshot(snapshot("A")); f.scope.advanceUntilIdle()
        assertEquals(1, f.executor.clicks.size)
    }

    @Test fun dry_run_never_calls_action_executor() {
        val f = fixture(); f.controller.startSession(SessionConfig.defaults().copy(dryRun = true))
        f.controller.submitSnapshot(snapshot("A")); f.scope.advanceUntilIdle()
        assertEquals(0, f.executor.clicks.size); assertEquals(1, f.controller.status.value.dryRunProcessed)
    }

    @Test fun dry_run_waits_for_a_different_fingerprint() {
        val f = fixture(); f.controller.startSession(SessionConfig.defaults())
        f.controller.submitSnapshot(snapshot("A")); f.scope.advanceUntilIdle(); f.controller.submitSnapshot(snapshot("A")); f.scope.advanceUntilIdle()
        assertEquals(1, f.controller.status.value.dryRunProcessed)
    }

    @Test fun ambiguous_match_never_clicks() {
        val f = fixture(); f.controller.startSession(SessionConfig.defaults().copy(dryRun = false))
        f.controller.submitSnapshot(snapshot("A", extraLike = true)); f.scope.advanceUntilIdle()
        assertEquals(0, f.executor.clicks.size); assertEquals(SessionPhase.ERROR, f.controller.status.value.phase)
    }

    @Test fun verification_screen_transitions_to_error_without_click() {
        val f = fixture(); f.controller.startSession(SessionConfig.defaults().copy(dryRun = false))
        val bad = snapshot("CAPTCHA").copy(nodes = snapshot("CAPTCHA").nodes + UiNode(NodeRef(listOf(3), null, null, "security check"), "TextView", null, null, "security check", false, true, false, "q"))
        f.controller.submitSnapshot(bad); f.scope.advanceUntilIdle()
        assertEquals(0, f.executor.clicks.size); assertEquals(SessionPhase.ERROR, f.controller.status.value.phase)
    }

    @Test fun new_session_resets_count_to_zero() {
        val f = fixture(); f.controller.startSession(SessionConfig.defaults().copy(dryRun = false)); f.controller.submitSnapshot(snapshot("A")); f.scope.advanceUntilIdle()
        assertEquals(1, f.controller.status.value.realLikes)
        f.controller.startSession(SessionConfig.defaults().copy(dryRun = false)); assertEquals(0, f.controller.status.value.realLikes)
    }

    @Test fun delay_is_requested_inside_configured_range() {
        val f = fixture(); f.controller.startSession(SessionConfig.defaults().copy(dryRun = false)); f.controller.submitSnapshot(snapshot("A")); f.scope.advanceUntilIdle()
        assertEquals(listOf(3_000L), f.delay.delays)
    }

    @Test fun package_switch_cancels_pending_action() {
        val f = fixture(); f.controller.startSession(SessionConfig.defaults().copy(dryRun = false)); f.controller.submitSnapshot(snapshot("A")); f.controller.submitSnapshot(snapshot("A", packageName = "other")); f.scope.advanceUntilIdle()
        assertEquals(0, f.executor.clicks.size)
    }

    @Test fun stop_is_idempotent() {
        val f = fixture(); f.controller.stopSession(); f.controller.stopSession(); assertEquals(SessionPhase.STOPPED, f.controller.status.value.phase)
    }
}
