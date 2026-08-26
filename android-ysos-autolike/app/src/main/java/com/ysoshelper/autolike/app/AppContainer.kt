package com.ysoshelper.autolike.app

import android.content.Context
import com.ysoshelper.autolike.automation.ServiceBridge
import com.ysoshelper.autolike.preferences.PreferencesRepository

class AppContainer(context: Context) {
    val preferences = PreferencesRepository(context.applicationContext)
    val serviceBridge = ServiceBridge()
}
