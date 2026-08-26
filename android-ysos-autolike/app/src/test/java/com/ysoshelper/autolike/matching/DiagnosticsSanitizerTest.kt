package com.ysoshelper.autolike.matching

import com.ysoshelper.autolike.accessibility.NodeRef
import com.ysoshelper.autolike.accessibility.UiNode
import com.ysoshelper.autolike.accessibility.UiSnapshot
import com.ysoshelper.autolike.automation.YSOS_PACKAGE
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DiagnosticsSanitizerTest {
    @Test fun password_content_is_removed_and_normal_fields_remain() {
        val long = "a".repeat(120)
        val s = UiSnapshot(YSOS_PACKAGE, listOf(
            UiNode(NodeRef(listOf(0), "id/a", null, long), "TextView", "id/a", null, long, true, true, false, "[0,0][1,1]"),
            UiNode(NodeRef(listOf(1), null, "secret-desc", "secret"), "EditText", null, "secret-desc", "secret", false, true, true, "[0,0][1,1]")
        ), 1)
        val out = s.toSanitizedDiagnostics()
        assertTrue(out.contains("id=id/a"))
        assertTrue(out.contains("clickable=true"))
        assertTrue(out.contains("a".repeat(80)))
        assertFalse(out.contains("a".repeat(81)))
        assertFalse(out.contains("secret"))
    }
}
