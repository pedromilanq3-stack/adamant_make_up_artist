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

guard_path = root / "app/src/main/java/com/ysoshelper/autolike/accessibility/SnapshotRootGuard.kt"
guard_path.write_text(
    '''package com.ysoshelper.autolike.accessibility

import com.ysoshelper.autolike.automation.YSOS_PACKAGE

object SnapshotRootGuard {
    fun shouldCapture(eventPackage: String?, rootPackage: String?): Boolean =
        eventPackage == YSOS_PACKAGE && rootPackage == YSOS_PACKAGE
}
'''
)

service_path = root / "app/src/main/java/com/ysoshelper/autolike/accessibility/YsosAccessibilityService.kt"
service = service_path.read_text()
old = '''        val root = rootInActiveWindow ?: return
        try {
            val snapshot = treeMapper.map(root, packageName, System.currentTimeMillis())
            latestSnapshot = snapshot
            controller.submitSnapshot(snapshot)
        } finally {
            @Suppress("DEPRECATION")
            root.recycle()
        }
'''
new = '''        val root = rootInActiveWindow ?: return
        try {
            val rootPackage = root.packageName?.toString()
            if (!SnapshotRootGuard.shouldCapture(packageName, rootPackage)) return

            val snapshot = treeMapper.map(root, packageName, System.currentTimeMillis())
            latestSnapshot = snapshot
            controller.submitSnapshot(snapshot)
        } finally {
            @Suppress("DEPRECATION")
            root.recycle()
        }
'''
if old not in service:
    raise SystemExit("Expected YsosAccessibilityService root capture block not found")
service_path.write_text(service.replace(old, new))
