package com.ysoshelper.autolike.matching

import com.ysoshelper.autolike.accessibility.NodeRef
import com.ysoshelper.autolike.accessibility.UiNode
import com.ysoshelper.autolike.accessibility.UiSnapshot
import com.ysoshelper.autolike.automation.YSOS_PACKAGE
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class ProfileIdentityTest {
    private val like = NodeRef(listOf(1), null, "Curtir", null)
    private fun snapshot(name: String, likeLabel: String = "Curtir", passwordText: String? = null) = UiSnapshot(
        YSOS_PACKAGE,
        listOf(
            UiNode(NodeRef(listOf(0), null, null, name), "TextView", null, null, name, false, true, false, "a"),
            UiNode(NodeRef(listOf(1), null, likeLabel, null), "Button", null, likeLabel, null, true, true, false, "b"),
            UiNode(NodeRef(listOf(2), null, null, passwordText), "EditText", null, null, passwordText, false, true, true, "c"),
        ), 0
    )

    @Test fun same_profile_metadata_produces_same_hash() {
        assertEquals(ProfileIdentity().fingerprint(snapshot("Ana"), like), ProfileIdentity().fingerprint(snapshot("Ana"), like))
    }

    @Test fun changed_visible_profile_text_changes_hash() {
        assertNotEquals(ProfileIdentity().fingerprint(snapshot("Ana"), like), ProfileIdentity().fingerprint(snapshot("Bia"), like))
    }

    @Test fun password_and_like_button_labels_are_excluded() {
        assertEquals(
            ProfileIdentity().fingerprint(snapshot("Ana", "Curtir", "secret1"), like),
            ProfileIdentity().fingerprint(snapshot("Ana", "Like", "secret2"), like.copy(contentDescription = "Like")),
        )
    }
}
