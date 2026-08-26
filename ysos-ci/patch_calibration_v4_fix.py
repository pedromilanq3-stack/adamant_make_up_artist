from pathlib import Path

ROOT = Path('android-app')

# 1) Preserve class/bounds in NodeRef so an unlabeled WebView control can be
# revalidated immediately before ACTION_CLICK.
p = ROOT / 'app/src/main/java/com/ysoshelper/autolike/accessibility/AccessibilityTreeMapper.kt'
s = p.read_text()
s = s.replace(
'''data class NodeRef(
    val path: List<Int>,
    val viewId: String?,
    val contentDescription: String?,
    val text: String?,
)''',
'''data class NodeRef(
    val path: List<Int>,
    val viewId: String?,
    val contentDescription: String?,
    val text: String?,
    val className: String? = null,
    val bounds: String? = null,
)''')
s = s.replace(
'''        val viewId = node.viewIdResourceName

        output += UiNode(
            ref = NodeRef(path, viewId, description, text),
            className = node.className?.toString(),''',
'''        val viewId = node.viewIdResourceName
        val className = node.className?.toString()
        val boundsText = "[${bounds.left},${bounds.top}][${bounds.right},${bounds.bottom}]"

        output += UiNode(
            ref = NodeRef(path, viewId, description, text, className, boundsText),
            className = className,''')
s = s.replace(
'''            bounds = "[${bounds.left},${bounds.top}][${bounds.right},${bounds.bottom}]",''',
'''            bounds = boundsText,''')
p.write_text(s)

# 2) Relax only the calibrated unlabeled WebView signature. Same path may move
# vertically; changed path must stay close in size and screen position.
p = ROOT / 'app/src/main/java/com/ysoshelper/autolike/matching/LikeCalibration.kt'
s = p.read_text()
old = '''    fun matches(node: UiNode): Boolean {
        if (!node.enabled || !node.clickable || node.password) return false
        if (className != null && node.className != className) return false

        viewId?.let { return node.viewId == it }
        contentDescription?.takeIf { it.isNotBlank() }?.let {
            return node.contentDescription == it
        }
        text?.takeIf { it.isNotBlank() }?.let {
            return node.text == it
        }

        if (path.isNotEmpty() && node.ref.path == path && node.bounds == bounds) return true
        return bounds.isNotBlank() && node.bounds == bounds
    }
'''
new = '''    fun matches(node: UiNode): Boolean {
        if (!node.enabled || !node.clickable || node.password) return false
        if (className != null && node.className != className) return false

        viewId?.let { return node.viewId == it }
        contentDescription?.takeIf { it.isNotBlank() }?.let {
            return node.contentDescription == it
        }
        text?.takeIf { it.isNotBlank() }?.let {
            return node.text == it
        }

        val calibratedRect = BoundsRect.parse(bounds) ?: return false
        val candidateRect = BoundsRect.parse(node.bounds) ?: return false

        if (path.isNotEmpty() && node.ref.path == path) {
            return calibratedRect.similarSize(candidateRect, 0.45) &&
                calibratedRect.centerXDistance(candidateRect) <= maxOf(120.0, calibratedRect.width * 0.9)
        }

        return calibratedRect.similarSize(candidateRect, 0.30) &&
            calibratedRect.centerXDistance(candidateRect) <= maxOf(90.0, calibratedRect.width * 0.65) &&
            calibratedRect.centerYDistance(candidateRect) <= maxOf(220.0, calibratedRect.height * 1.75)
    }

    private data class BoundsRect(
        val left: Int,
        val top: Int,
        val right: Int,
        val bottom: Int,
    ) {
        val width: Double get() = (right - left).toDouble()
        val height: Double get() = (bottom - top).toDouble()
        private val centerX: Double get() = (left + right) / 2.0
        private val centerY: Double get() = (top + bottom) / 2.0

        fun similarSize(other: BoundsRect, tolerance: Double): Boolean {
            if (width <= 0 || height <= 0 || other.width <= 0 || other.height <= 0) return false
            val widthDelta = kotlin.math.abs(width - other.width) / width
            val heightDelta = kotlin.math.abs(height - other.height) / height
            return widthDelta <= tolerance && heightDelta <= tolerance
        }

        fun centerXDistance(other: BoundsRect): Double = kotlin.math.abs(centerX - other.centerX)
        fun centerYDistance(other: BoundsRect): Double = kotlin.math.abs(centerY - other.centerY)

        companion object {
            private val pattern = Regex("""^\\[(-?\\d+),(-?\\d+)]\\[(-?\\d+),(-?\\d+)]$""")

            fun parse(value: String): BoundsRect? {
                val match = pattern.matchEntire(value.trim()) ?: return null
                val (left, top, right, bottom) = match.destructured
                return BoundsRect(
                    left = left.toIntOrNull() ?: return null,
                    top = top.toIntOrNull() ?: return null,
                    right = right.toIntOrNull() ?: return null,
                    bottom = bottom.toIntOrNull() ?: return null,
                )
            }
        }
    }
'''
if old not in s:
    raise SystemExit('Expected LikeCalibration.matches block not found')
p.write_text(s.replace(old, new))

# 3) Guard the final click. Semantic buttons still require exact semantics;
# unlabeled calibrated buttons require exact class + bounds from the latest
# revalidated snapshot.
p = ROOT / 'app/src/main/java/com/ysoshelper/autolike/accessibility/ActionTargetGuard.kt'
p.write_text('''package com.ysoshelper.autolike.accessibility

data class ObservedActionNode(
    val className: String?,
    val viewId: String?,
    val contentDescription: String?,
    val text: String?,
    val bounds: String,
    val clickable: Boolean,
    val enabled: Boolean,
    val password: Boolean,
)

object ActionTargetGuard {
    fun canClick(target: NodeRef, observed: ObservedActionNode): Boolean {
        if (!observed.enabled || !observed.clickable || observed.password) return false
        target.className?.let { if (observed.className != it) return false }
        target.bounds?.let { if (observed.bounds != it) return false }

        val semanticExpectations = buildList {
            target.viewId?.let { expected -> add(observed.viewId == expected) }
            target.contentDescription?.let { expected -> add(observed.contentDescription == expected) }
            target.text?.let { expected -> add(observed.text == expected) }
        }
        if (semanticExpectations.isNotEmpty()) return semanticExpectations.all { it }
        return target.className != null && target.bounds != null
    }
}
''')

p = ROOT / 'app/src/main/java/com/ysoshelper/autolike/accessibility/AndroidActionExecutor.kt'
s = p.read_text()
if 'import android.graphics.Rect' not in s:
    s = s.replace('import android.view.accessibility.AccessibilityNodeInfo\n', 'import android.graphics.Rect\nimport android.view.accessibility.AccessibilityNodeInfo\n')
old = '''            if (!current.isEnabled || !current.isClickable || current.isPassword) return false

            val checks = buildList {
                target.viewId?.let { expected -> add(current.viewIdResourceName == expected) }
                target.contentDescription?.let { expected -> add(current.contentDescription?.toString() == expected) }
                target.text?.let { expected -> add(current.text?.toString() == expected) }
            }
            if (checks.isEmpty() || checks.none { it }) return false

            current.performAction(AccessibilityNodeInfo.ACTION_CLICK)
'''
new = '''            val rect = Rect().also(current::getBoundsInScreen)
            val observed = ObservedActionNode(
                className = current.className?.toString(),
                viewId = current.viewIdResourceName,
                contentDescription = current.contentDescription?.toString(),
                text = current.text?.toString(),
                bounds = "[${rect.left},${rect.top}][${rect.right},${rect.bottom}]",
                clickable = current.isClickable,
                enabled = current.isEnabled,
                password = current.isPassword,
            )
            if (!ActionTargetGuard.canClick(target, observed)) return false

            current.performAction(AccessibilityNodeInfo.ACTION_CLICK)
'''
if old not in s:
    raise SystemExit('Expected AndroidActionExecutor verification block not found')
p.write_text(s.replace(old, new))

# 4) Regression tests for final unlabeled click guard.
p = ROOT / 'app/src/test/java/com/ysoshelper/autolike/accessibility/ActionTargetGuardTest.kt'
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text('''package com.ysoshelper.autolike.accessibility

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ActionTargetGuardTest {
    private val target = NodeRef(
        path = listOf(0, 0, 0, 25),
        viewId = null,
        contentDescription = null,
        text = null,
        className = "android.widget.Button",
        bounds = "[470,2018][609,2157]",
    )

    private fun observed(
        className: String = "android.widget.Button",
        bounds: String = "[470,2018][609,2157]",
    ) = ObservedActionNode(
        className = className,
        viewId = null,
        contentDescription = null,
        text = null,
        bounds = bounds,
        clickable = true,
        enabled = true,
        password = false,
    )

    @Test fun allows_revalidated_unlabelled_webview_button() =
        assertTrue(ActionTargetGuard.canClick(target, observed()))

    @Test fun rejects_if_bounds_changed_after_revalidation() =
        assertFalse(ActionTargetGuard.canClick(target, observed(bounds = "[470,1900][609,2039]")))

    @Test fun rejects_if_class_changed_after_revalidation() =
        assertFalse(ActionTargetGuard.canClick(target, observed(className = "android.widget.ImageButton")))
}
''')

# 5) Version bump.
p = ROOT / 'app/build.gradle.kts'
s = p.read_text().replace('versionCode = 3', 'versionCode = 4').replace('versionName = "0.3.0"', 'versionName = "0.4.0"')
p.write_text(s)

print('Applied YSOS AutoLike v0.4.0 WebView calibration fix')
