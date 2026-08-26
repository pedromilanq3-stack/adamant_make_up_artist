package com.ysoshelper.autolike.automation

import kotlinx.coroutines.flow.StateFlow

interface AutomationPort {
    val status: StateFlow<SessionStatus>
    fun startSession(config: SessionConfig): ConfigValidation
    fun stopSession(reason: String = "Stopped by user")
    fun diagnosticsText(): String
    fun sessionLogText(): String
}
