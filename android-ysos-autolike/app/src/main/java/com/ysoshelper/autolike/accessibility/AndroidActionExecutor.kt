package com.ysoshelper.autolike.accessibility

import android.view.accessibility.AccessibilityNodeInfo
import com.ysoshelper.autolike.automation.ActionExecutor
import com.ysoshelper.autolike.automation.DelayProvider
import com.ysoshelper.autolike.automation.RandomDelay
import kotlinx.coroutines.delay
import kotlin.random.Random

class AndroidActionExecutor(
    private val rootProvider: () -> AccessibilityNodeInfo?,
) : ActionExecutor {
    override suspend fun click(target: NodeRef): Boolean {
        var node = rootProvider() ?: return false
        target.path.forEach { index ->
            node = node.getChild(index) ?: return false
        }
        if (!node.isEnabled || !node.isClickable || node.isPassword) return false

        val confirmations = buildList {
            target.viewId?.let { expected -> add(node.viewIdResourceName == expected) }
            target.contentDescription?.let { expected -> add(node.contentDescription?.toString()?.take(80) == expected) }
            target.text?.let { expected -> add(node.text?.toString()?.take(80) == expected) }
        }
        if (confirmations.isEmpty() || confirmations.none { it }) return false
        return node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
    }
}

class CoroutineDelayProvider : DelayProvider {
    override suspend fun delayMs(ms: Long) = delay(ms)
}

class KotlinRandomDelay : RandomDelay {
    override fun nextDelayMs(minMs: Long, maxMs: Long): Long =
        if (minMs == maxMs) minMs else Random.nextLong(minMs, maxMs + 1)
}
