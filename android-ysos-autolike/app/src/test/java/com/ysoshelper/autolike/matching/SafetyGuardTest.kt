package com.ysoshelper.autolike.matching

import com.ysoshelper.autolike.accessibility.NodeRef
import com.ysoshelper.autolike.accessibility.UiNode
import com.ysoshelper.autolike.accessibility.UiSnapshot
import com.ysoshelper.autolike.automation.YSOS_PACKAGE
import org.junit.Assert.assertTrue
import org.junit.Test

class SafetyGuardTest {
    private fun snapshot(pkg: String = YSOS_PACKAGE, text: String = "Perfil") = UiSnapshot(
        pkg,
        listOf(UiNode(NodeRef(listOf(0), null, null, text), "TextView", null, null, text, false, true, false, "x")),
        0,
    )

    @Test fun verification_copy_blocks_session() {
        assertTrue(SafetyGuard().inspect(snapshot(text = "Verificação necessária")) is SafetyDecision.Stop)
    }

    @Test fun ordinary_profile_copy_is_safe() {
        assertTrue(SafetyGuard().inspect(snapshot()) is SafetyDecision.Safe)
    }

    @Test fun non_ysos_package_is_blocked() {
        assertTrue(SafetyGuard().inspect(snapshot(pkg = "other")) is SafetyDecision.Stop)
    }
}
