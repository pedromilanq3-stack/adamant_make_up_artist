package com.ysoshelper.autolike.automation

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SessionConfigTest {
    @Test fun defaults_match_spec() {
        val config = SessionConfig.defaults()
        assertEquals(50, config.limit)
        assertEquals(3_000L, config.minDelayMs)
        assertEquals(7_000L, config.maxDelayMs)
        assertTrue(config.dryRun)
        assertFalse(config.debug)
    }

    @Test fun rejects_limit_outside_1_to_100() {
        assertTrue(SessionConfig.defaults().copy(limit = 0).validate() is ConfigValidation.Invalid)
        assertTrue(SessionConfig.defaults().copy(limit = 101).validate() is ConfigValidation.Invalid)
    }

    @Test fun rejects_invalid_delay_range() {
        assertTrue(SessionConfig.defaults().copy(minDelayMs = 8_000, maxDelayMs = 7_000).validate() is ConfigValidation.Invalid)
        assertTrue(SessionConfig.defaults().copy(minDelayMs = 0).validate() is ConfigValidation.Invalid)
    }
}
