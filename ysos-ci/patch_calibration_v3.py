from pathlib import Path

root = Path('android-app')
test_path = root / 'app/src/test/java/com/ysoshelper/autolike/matching/CalibrationFeatureContractTest.kt'
test_path.parent.mkdir(parents=True, exist_ok=True)
test_path.write_text(r'''package com.ysoshelper.autolike.matching

import com.ysoshelper.autolike.accessibility.NodeRef
import com.ysoshelper.autolike.accessibility.UiNode
import com.ysoshelper.autolike.accessibility.UiSnapshot
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertNotNull
import org.junit.Assert.fail
import org.junit.Test

class CalibrationFeatureContractTest {
    private fun button(path: List<Int>, bounds: String) = UiNode(
        ref = NodeRef(path, null, null, null),
        className = "android.widget.Button",
        viewId = null,
        contentDescription = null,
        text = null,
        clickable = true,
        enabled = true,
        password = false,
        bounds = bounds,
    )

    @Test
    fun captures_exact_unlabelled_webview_button() {
        val target = button(listOf(0, 0, 0, 25), "[470,2018][609,2157]")
        val other = button(listOf(0, 0, 0, 17), "[46,1584][65,1601]")
        val calibration = resolve(UiSnapshot("br.com.esapiens.ysos", listOf(target, other), 1L), target)
        assertNotNull(calibration)
        val path = calibration!!.javaClass.getMethod("getPath").invoke(calibration)
        assertEquals(listOf(0, 0, 0, 25), path)
    }

    @Test
    fun refuses_ambiguous_click_fingerprint() {
        val a = button(listOf(0, 0, 0, 25), "[470,2018][609,2157]")
        val b = button(listOf(0, 0, 0, 26), "[470,2018][609,2157]")
        assertNull(resolve(UiSnapshot("br.com.esapiens.ysos", listOf(a, b), 1L), a))
    }

    @Test
    fun calibrated_matcher_selects_only_the_recorded_unlabelled_button() {
        val target = button(listOf(0, 0, 0, 25), "[470,2018][609,2157]")
        val other = button(listOf(0, 0, 0, 17), "[46,1584][65,1601]")
        val snapshot = UiSnapshot("br.com.esapiens.ysos", listOf(target, other), 1L)
        val calibration = resolve(snapshot, target) ?: fail("CalibrationCapture did not resolve target")

        val constructor = try {
            YsosUiMatcher::class.java.getConstructor(kotlin.jvm.functions.Function0::class.java)
        } catch (_: NoSuchMethodException) {
            fail("YsosUiMatcher has no calibration provider constructor")
            error("unreachable")
        }
        val provider = object : kotlin.jvm.functions.Function0<Any?> {
            override fun invoke(): Any? = calibration
        }
        val matcher = constructor.newInstance(provider) as YsosUiMatcher
        val match = matcher.resolveLike(snapshot)
        if (match !is LikeMatch.Unique) fail("Expected calibrated unlabeled button to resolve uniquely, got $match")
        assertEquals(target.ref, (match as LikeMatch.Unique).target)
    }

    private fun resolve(snapshot: UiSnapshot, source: UiNode): Any? {
        val captureClass = try {
            Class.forName("com.ysoshelper.autolike.matching.CalibrationCapture")
        } catch (_: ClassNotFoundException) {
            fail("CalibrationCapture is missing")
            error("unreachable")
        }
        val instance = captureClass.getField("INSTANCE").get(null)
        val method = captureClass.getDeclaredMethod(
            "resolve",
            UiSnapshot::class.java,
            String::class.java,
            String::class.java,
            String::class.java,
            String::class.java,
            String::class.java,
        )
        return method.invoke(
            instance,
            snapshot,
            source.className,
            source.viewId,
            source.contentDescription,
            source.text,
            source.bounds,
        )
    }
}
''')
