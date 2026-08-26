from pathlib import Path

p = Path('android-app/app/src/test/java/com/ysoshelper/autolike/matching/CalibrationFeatureContractTest.kt')
s = p.read_text()
marker = '\n}\n'
insert = r'''

    @Test
    fun calibrated_matcher_tolerates_small_webview_layout_drift() {
        val original = button(listOf(0, 0, 0, 25), "[470,2018][609,2157]")
        val calibration = resolve(
            UiSnapshot("br.com.esapiens.ysos", listOf(original), 1L),
            original,
        ) ?: fail("CalibrationCapture did not resolve original heart")

        // WebView profiles can move the same visual control a few pixels and
        // can change its DOM/accessibility index between profiles.
        val shiftedHeart = button(listOf(0, 0, 0, 24), "[476,2024][615,2163]")
        val unrelated = button(listOf(0, 0, 0, 17), "[46,1584][65,1601]")
        val snapshot = UiSnapshot(
            "br.com.esapiens.ysos",
            listOf(shiftedHeart, unrelated),
            2L,
        )

        val constructor = YsosUiMatcher::class.java.getConstructor(kotlin.jvm.functions.Function0::class.java)
        val provider = object : kotlin.jvm.functions.Function0<Any?> {
            override fun invoke(): Any? = calibration
        }
        val matcher = constructor.newInstance(provider) as YsosUiMatcher
        val match = matcher.resolveLike(snapshot)

        if (match !is LikeMatch.Unique) fail("Expected shifted calibrated heart to resolve uniquely, got $match")
        assertEquals(shiftedHeart.ref, (match as LikeMatch.Unique).target)
    }
'''
idx = s.rfind(marker)
if idx == -1:
    raise SystemExit('Could not locate CalibrationFeatureContractTest closing brace')
p.write_text(s[:idx] + insert + s[idx:])
