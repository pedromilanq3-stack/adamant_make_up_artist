package com.ysoshelper.autolike.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.ysoshelper.autolike.automation.SessionPhase

private val activePhases = setOf(
    SessionPhase.ARMED,
    SessionPhase.WAITING_FOR_PROFILE,
    SessionPhase.DELAYING,
    SessionPhase.REVALIDATING,
    SessionPhase.ACTING,
    SessionPhase.WAITING_FOR_NEXT_PROFILE,
    SessionPhase.DRY_RUN,
)

@Composable
fun MainScreen(
    state: MainUiState,
    onLimitChange: (String) -> Unit,
    onMinDelayChange: (String) -> Unit,
    onMaxDelayChange: (String) -> Unit,
    onDryRunChange: (Boolean) -> Unit,
    onDebugChange: (Boolean) -> Unit,
    onEnableAccessibility: () -> Unit,
    onOpenYsos: () -> Unit,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onDiagnostics: () -> Unit,
    onExportLog: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("YSOS AutoLike", fontWeight = FontWeight.Bold)
        Text("Accessibility: ${if (state.serviceEnabled) "Enabled" else "Disabled"}")
        Text("Session: ${state.phase}")
        HorizontalDivider()

        OutlinedTextField(
            value = state.limit,
            onValueChange = onLimitChange,
            label = { Text("Session limit (1–100)") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            OutlinedTextField(
                value = state.minDelaySeconds,
                onValueChange = onMinDelayChange,
                label = { Text("Min delay (s)") },
                singleLine = true,
                modifier = Modifier.weight(1f),
            )
            OutlinedTextField(
                value = state.maxDelaySeconds,
                onValueChange = onMaxDelayChange,
                label = { Text("Max delay (s)") },
                singleLine = true,
                modifier = Modifier.weight(1f),
            )
        }
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            Text("Dry Run", modifier = Modifier.weight(1f))
            Switch(checked = state.dryRun, onCheckedChange = onDryRunChange)
        }
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            Text("Debug diagnostics", modifier = Modifier.weight(1f))
            Switch(checked = state.debug, onCheckedChange = onDebugChange)
        }

        if (state.dryRun) {
            Text("Dry Run processed: ${state.dryRunProcessed} (no automatic clicks)")
        } else {
            Text("Likes: ${state.realLikes} / ${state.sessionLimit}", fontWeight = FontWeight.Bold)
        }
        Text(state.lastMessage)
        Spacer(Modifier.height(4.dp))

        Button(onClick = onEnableAccessibility, modifier = Modifier.fillMaxWidth()) { Text("Enable Accessibility") }
        Button(onClick = onOpenYsos, modifier = Modifier.fillMaxWidth()) { Text("Open YSOS") }
        Button(
            onClick = onStart,
            enabled = state.serviceEnabled && state.phase !in activePhases,
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Start Session") }
        Button(
            onClick = onStop,
            enabled = state.phase in activePhases,
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Stop Session") }
        Button(onClick = onDiagnostics, modifier = Modifier.fillMaxWidth()) { Text("UI Diagnostics") }
        Button(onClick = onExportLog, modifier = Modifier.fillMaxWidth()) { Text("Export Log") }
    }
}
