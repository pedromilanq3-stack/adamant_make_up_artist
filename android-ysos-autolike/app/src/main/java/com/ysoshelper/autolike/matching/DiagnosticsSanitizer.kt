package com.ysoshelper.autolike.matching

import com.ysoshelper.autolike.accessibility.UiSnapshot

fun UiSnapshot.toSanitizedDiagnostics(): String = buildString {
    append("package=").append(packageName)
        .append(" capturedAtMs=").append(capturedAtMs).append('\n')
    nodes.forEach { node ->
        val safeText = if (node.password) "" else node.text.orEmpty().take(80)
        val safeDesc = if (node.password) "" else node.contentDescription.orEmpty().take(80)
        append("path=").append(node.ref.path.joinToString("/"))
            .append(" class=").append(node.className.orEmpty())
            .append(" id=").append(node.viewId.orEmpty())
            .append(" clickable=").append(node.clickable)
            .append(" enabled=").append(node.enabled)
            .append(" bounds=").append(node.bounds)
            .append(" text=\"").append(safeText.replace("\"", "'"))
            .append("\" desc=\"").append(safeDesc.replace("\"", "'"))
            .append("\"\n")
    }
}
