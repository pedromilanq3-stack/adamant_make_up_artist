package com.ysoshelper.autolike.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun UiDiagnosticsScreen(
    text: String,
    onRefresh: () -> Unit,
    onCopy: () -> Unit,
    onShare: () -> Unit,
    onBack: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("UI Diagnostics")
        Text("Diagnostics contain accessibility labels, not screenshots.")
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            Button(onClick = onRefresh, modifier = Modifier.weight(1f)) { Text("Refresh") }
            Button(onClick = onCopy, modifier = Modifier.weight(1f)) { Text("Copy") }
            Button(onClick = onShare, modifier = Modifier.weight(1f)) { Text("Share") }
        }
        Button(onClick = onBack) { Text("Back") }
        Text(text)
    }
}
