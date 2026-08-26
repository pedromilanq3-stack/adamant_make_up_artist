from pathlib import Path

root = Path("android-app")
test_path = root / "app/src/test/java/com/ysoshelper/autolike/accessibility/SnapshotRootGuardContractTest.kt"
test_path.parent.mkdir(parents=True, exist_ok=True)
test_path.write_text(
    '''package com.ysoshelper.autolike.accessibility

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test

class SnapshotRootGuardContractTest {
    @Test
    fun rejects_launcher_root_when_event_package_is_ysos() {
        val (instance, method) = guardMethod()
        val accepted = method.invoke(
            instance,
            "br.com.esapiens.ysos",
            "com.motorola.launcher3",
        ) as Boolean
        assertFalse(accepted)
    }

    @Test
    fun accepts_ysos_root_when_event_package_is_ysos() {
        val (instance, method) = guardMethod()
        val accepted = method.invoke(
            instance,
            "br.com.esapiens.ysos",
            "br.com.esapiens.ysos",
        ) as Boolean
        assertTrue(accepted)
    }

    private fun guardMethod(): Pair<Any, java.lang.reflect.Method> {
        val guardClass = try {
            Class.forName("com.ysoshelper.autolike.accessibility.SnapshotRootGuard")
        } catch (_: ClassNotFoundException) {
            fail("SnapshotRootGuard is missing; a YSOS event can still be paired with another app's active root")
            error("unreachable")
        }
        val instance = guardClass.getField("INSTANCE").get(null)
        val method = guardClass.getDeclaredMethod(
            "shouldCapture",
            String::class.java,
            String::class.java,
        )
        return instance to method
    }
}
'''
)
