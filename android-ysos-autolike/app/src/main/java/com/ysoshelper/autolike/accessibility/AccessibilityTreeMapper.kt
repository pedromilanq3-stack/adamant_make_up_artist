package com.ysoshelper.autolike.accessibility

import android.graphics.Rect
import android.view.accessibility.AccessibilityNodeInfo

data class NodeRef(
    val path: List<Int>,
    val viewId: String?,
    val contentDescription: String?,
    val text: String?,
)

data class UiNode(
    val ref: NodeRef,
    val className: String?,
    val viewId: String?,
    val contentDescription: String?,
    val text: String?,
    val clickable: Boolean,
    val enabled: Boolean,
    val password: Boolean,
    val bounds: String,
)

data class UiSnapshot(
    val packageName: String,
    val nodes: List<UiNode>,
    val capturedAtMs: Long,
)

class AccessibilityTreeMapper {
    fun map(root: AccessibilityNodeInfo, packageName: String, nowMs: Long): UiSnapshot {
        val nodes = ArrayList<UiNode>()
        visit(root, emptyList(), nodes)
        return UiSnapshot(packageName = packageName, nodes = nodes, capturedAtMs = nowMs)
    }

    private fun visit(node: AccessibilityNodeInfo, path: List<Int>, out: MutableList<UiNode>) {
        val password = node.isPassword
        val text = if (password) null else short(node.text)
        val description = if (password) null else short(node.contentDescription)
        val rect = Rect()
        node.getBoundsInScreen(rect)
        val ref = NodeRef(
            path = path,
            viewId = node.viewIdResourceName,
            contentDescription = description,
            text = text,
        )
        out += UiNode(
            ref = ref,
            className = node.className?.toString(),
            viewId = node.viewIdResourceName,
            contentDescription = description,
            text = text,
            clickable = node.isClickable,
            enabled = node.isEnabled,
            password = password,
            bounds = rect.toShortString(),
        )
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            visit(child, path + i, out)
        }
    }

    private fun short(value: CharSequence?): String? = value
        ?.toString()
        ?.replace(Regex("\\s+"), " ")
        ?.trim()
        ?.takeIf { it.isNotEmpty() }
        ?.take(80)
}
