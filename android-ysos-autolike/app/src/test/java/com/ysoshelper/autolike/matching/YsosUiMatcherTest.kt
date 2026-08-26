package com.ysoshelper.autolike.matching

import com.ysoshelper.autolike.accessibility.NodeRef
import com.ysoshelper.autolike.accessibility.UiNode
import com.ysoshelper.autolike.accessibility.UiSnapshot
import com.ysoshelper.autolike.automation.YSOS_PACKAGE
import org.junit.Assert.assertTrue
import org.junit.Test

class YsosUiMatcherTest {
    private fun node(path: Int, label: String, clickable: Boolean = true, enabled: Boolean = true) = UiNode(
        ref = NodeRef(listOf(path), null, label, null),
        className = "android.widget.Button", viewId = null, contentDescription = label, text = null,
        clickable = clickable, enabled = enabled, password = false, bounds = "[0,0][1,1]"
    )

    @Test fun exact_like_label_resolves_unique_button() {
        val s = UiSnapshot(YSOS_PACKAGE, listOf(node(0, "Curtir")), 0)
        assertTrue(YsosUiMatcher().resolveLike(s) is LikeMatch.Unique)
    }

    @Test fun two_like_candidates_are_ambiguous() {
        val s = UiSnapshot(YSOS_PACKAGE, listOf(node(0, "Curtir"), node(1, "Like")), 0)
        assertTrue(YsosUiMatcher().resolveLike(s) is LikeMatch.Ambiguous)
    }

    @Test fun disabled_like_node_is_not_actionable() {
        val s = UiSnapshot(YSOS_PACKAGE, listOf(node(0, "Curtir", enabled = false)), 0)
        assertTrue(YsosUiMatcher().resolveLike(s) is LikeMatch.None)
    }

    @Test fun other_package_never_resolves() {
        val s = UiSnapshot("example.other", listOf(node(0, "Curtir")), 0)
        assertTrue(YsosUiMatcher().resolveLike(s) is LikeMatch.None)
    }
}
