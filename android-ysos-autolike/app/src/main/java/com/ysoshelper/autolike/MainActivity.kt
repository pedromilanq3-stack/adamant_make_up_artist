package com.ysoshelper.autolike

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.core.content.FileProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ysoshelper.autolike.automation.YSOS_PACKAGE
import com.ysoshelper.autolike.ui.MainScreen
import com.ysoshelper.autolike.ui.MainViewModel
import com.ysoshelper.autolike.ui.UiDiagnosticsScreen
import com.ysoshelper.autolike.ui.theme.YsosAutoLikeTheme
import java.io.File

class MainActivity : ComponentActivity() {
    private val viewModel: MainViewModel by viewModels {
        val container = (application as YsosAutoLikeApplication).container
        MainViewModel.Factory(container.preferences, container.serviceBridge)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            YsosAutoLikeTheme {
                val state by viewModel.uiState.collectAsStateWithLifecycle()
                var diagnostics by remember { mutableStateOf<String?>(null) }
                if (diagnostics != null) {
                    UiDiagnosticsScreen(
                        text = diagnostics.orEmpty(),
                        onRefresh = { diagnostics = viewModel.diagnosticsText() },
                        onCopy = { copyText(diagnostics.orEmpty()) },
                        onShare = { sharePlainText("YSOS AutoLike diagnostics", diagnostics.orEmpty()) },
                        onBack = { diagnostics = null },
                    )
                } else {
                    MainScreen(
                        state = state,
                        onLimitChange = viewModel::setLimit,
                        onMinDelayChange = viewModel::setMinDelay,
                        onMaxDelayChange = viewModel::setMaxDelay,
                        onDryRunChange = viewModel::setDryRun,
                        onDebugChange = viewModel::setDebug,
                        onEnableAccessibility = {
                            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
                        },
                        onOpenYsos = ::openYsos,
                        onStart = viewModel::startSession,
                        onStop = viewModel::stopSession,
                        onDiagnostics = { diagnostics = viewModel.diagnosticsText() },
                        onExportLog = { exportLog(viewModel.sessionLogText()) },
                    )
                }
            }
        }
    }

    private fun openYsos() {
        val intent = packageManager.getLaunchIntentForPackage(YSOS_PACKAGE)
        if (intent == null) {
            viewModel.reportMessage("YSOS is not installed")
        } else {
            startActivity(intent)
        }
    }

    private fun copyText(text: String) {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("YSOS AutoLike diagnostics", text))
    }

    private fun sharePlainText(subject: String, text: String) {
        startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, subject)
            putExtra(Intent.EXTRA_TEXT, text)
        }, subject))
    }

    private fun exportLog(text: String) {
        val dir = File(cacheDir, "exports").apply { mkdirs() }
        val file = File(dir, "session-log.txt").apply { writeText(text) }
        val uri = FileProvider.getUriForFile(this, "$packageName.fileprovider", file)
        startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }, "Export session log"))
    }
}
