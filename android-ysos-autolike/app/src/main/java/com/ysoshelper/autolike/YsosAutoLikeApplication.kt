package com.ysoshelper.autolike

import android.app.Application
import com.ysoshelper.autolike.app.AppContainer

class YsosAutoLikeApplication : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }
}
