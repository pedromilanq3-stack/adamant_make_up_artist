package com.ysoshelper.autolike.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.ysoshelper.autolike.automation.ConfigValidation
import com.ysoshelper.autolike.automation.ServiceBridge
import com.ysoshelper.autolike.automation.SessionConfig
import com.ysoshelper.autolike.automation.SessionPhase
import com.ysoshelper.autolike.preferences.PreferencesRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

data class MainUiState(
    val limit: String = "50",
    val minDelaySeconds: String = "3",
    val maxDelaySeconds: String = "7",
    val dryRun: Boolean = true,
    val debug: Boolean = false,
    val serviceEnabled: Boolean = false,
    val phase: SessionPhase = SessionPhase.STOPPED,
    val realLikes: Int = 0,
    val dryRunProcessed: Int = 0,
    val sessionLimit: Int = 50,
    val lastMessage: String = "Stopped",
)

class MainViewModel(
    private val preferences: PreferencesRepository,
    private val bridge: ServiceBridge,
) : ViewModel() {
    private val _uiState = MutableStateFlow(MainUiState())
    val uiState: StateFlow<MainUiState> = _uiState.asStateFlow()
    private var loadedPreferences = false

    init {
        viewModelScope.launch {
            preferences.preferences.collect { prefs ->
                if (!loadedPreferences) {
                    loadedPreferences = true
                    val c = prefs.sessionConfig
                    _uiState.value = _uiState.value.copy(
                        limit = c.limit.toString(),
                        minDelaySeconds = (c.minDelayMs / 1000L).toString(),
                        maxDelaySeconds = (c.maxDelayMs / 1000L).toString(),
                        dryRun = c.dryRun,
                        debug = c.debug,
                        sessionLimit = c.limit,
                    )
                }
            }
        }
        viewModelScope.launch {
            bridge.port.collectLatest { port ->
                _uiState.value = _uiState.value.copy(serviceEnabled = port != null)
                if (port == null) {
                    _uiState.value = _uiState.value.copy(
                        phase = SessionPhase.STOPPED,
                        realLikes = 0,
                        dryRunProcessed = 0,
                        lastMessage = "Accessibility service disabled",
                    )
                } else {
                    port.status.collect { status ->
                        _uiState.value = _uiState.value.copy(
                            phase = status.phase,
                            realLikes = status.realLikes,
                            dryRunProcessed = status.dryRunProcessed,
                            sessionLimit = status.limit,
                            lastMessage = status.lastMessage,
                        )
                    }
                }
            }
        }
    }

    fun setLimit(value: String) { _uiState.value = _uiState.value.copy(limit = value.filter(Char::isDigit).take(3)) }
    fun setMinDelay(value: String) { _uiState.value = _uiState.value.copy(minDelaySeconds = value.filter(Char::isDigit).take(3)) }
    fun setMaxDelay(value: String) { _uiState.value = _uiState.value.copy(maxDelaySeconds = value.filter(Char::isDigit).take(3)) }
    fun setDryRun(value: Boolean) { _uiState.value = _uiState.value.copy(dryRun = value) }
    fun setDebug(value: Boolean) { _uiState.value = _uiState.value.copy(debug = value) }

    fun startSession() {
        val state = _uiState.value
        val cfg = SessionConfig(
            limit = state.limit.toIntOrNull() ?: 0,
            minDelayMs = (state.minDelaySeconds.toLongOrNull() ?: 0L) * 1000L,
            maxDelayMs = (state.maxDelaySeconds.toLongOrNull() ?: 0L) * 1000L,
            dryRun = state.dryRun,
            debug = state.debug,
        )
        val port = bridge.port.value
        if (port == null) {
            _uiState.value = state.copy(lastMessage = "Enable Accessibility first")
            return
        }
        when (val result = port.startSession(cfg)) {
            ConfigValidation.Valid -> viewModelScope.launch { preferences.saveSessionConfig(cfg) }
            is ConfigValidation.Invalid -> _uiState.value = state.copy(lastMessage = result.message)
        }
    }

    fun stopSession() {
        bridge.port.value?.stopSession() ?: run {
            _uiState.value = _uiState.value.copy(lastMessage = "Already stopped")
        }
    }

    fun reportMessage(message: String) {
        _uiState.value = _uiState.value.copy(lastMessage = message)
    }

    fun diagnosticsText(): String = bridge.port.value?.diagnosticsText()
        ?: "Accessibility service is not connected"

    fun sessionLogText(): String = bridge.port.value?.sessionLogText()
        ?: "No session log available"

    class Factory(
        private val preferences: PreferencesRepository,
        private val bridge: ServiceBridge,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            MainViewModel(preferences, bridge) as T
    }
}
