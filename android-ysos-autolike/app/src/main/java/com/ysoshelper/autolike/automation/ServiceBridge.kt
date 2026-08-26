package com.ysoshelper.autolike.automation

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class ServiceBridge {
    private val _port = MutableStateFlow<AutomationPort?>(null)
    val port: StateFlow<AutomationPort?> = _port.asStateFlow()

    fun register(port: AutomationPort) {
        _port.value = port
    }

    fun unregister(port: AutomationPort) {
        if (_port.value === port) _port.value = null
    }
}
