package com.ysoshelper.autolike.preferences

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.ysoshelper.autolike.automation.SessionConfig
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.ysosAutoLikeDataStore by preferencesDataStore(name = "ysos_autolike_settings")

data class AppPreferences(
    val sessionConfig: SessionConfig = SessionConfig.defaults(),
    val onboardingComplete: Boolean = false,
)

class PreferencesRepository private constructor(
    private val dataStore: DataStore<Preferences>,
) {
    constructor(context: Context) : this(context.ysosAutoLikeDataStore)

    val preferences: Flow<AppPreferences> = dataStore.data.map { p ->
        val defaults = SessionConfig.defaults()
        AppPreferences(
            sessionConfig = SessionConfig(
                limit = p[Keys.LIMIT] ?: defaults.limit,
                minDelayMs = p[Keys.MIN_DELAY_MS] ?: defaults.minDelayMs,
                maxDelayMs = p[Keys.MAX_DELAY_MS] ?: defaults.maxDelayMs,
                dryRun = p[Keys.DRY_RUN] ?: defaults.dryRun,
                debug = p[Keys.DEBUG] ?: defaults.debug,
            ),
            onboardingComplete = p[Keys.ONBOARDING_COMPLETE] ?: false,
        )
    }

    suspend fun saveSessionConfig(config: SessionConfig) {
        dataStore.edit { p ->
            p[Keys.LIMIT] = config.limit
            p[Keys.MIN_DELAY_MS] = config.minDelayMs
            p[Keys.MAX_DELAY_MS] = config.maxDelayMs
            p[Keys.DRY_RUN] = config.dryRun
            p[Keys.DEBUG] = config.debug
        }
    }

    suspend fun markOnboardingComplete() {
        dataStore.edit { it[Keys.ONBOARDING_COMPLETE] = true }
    }

    private object Keys {
        val LIMIT = intPreferencesKey("limit")
        val MIN_DELAY_MS = longPreferencesKey("min_delay_ms")
        val MAX_DELAY_MS = longPreferencesKey("max_delay_ms")
        val DRY_RUN = booleanPreferencesKey("dry_run")
        val DEBUG = booleanPreferencesKey("debug")
        val ONBOARDING_COMPLETE = booleanPreferencesKey("onboarding_complete")
    }
}
