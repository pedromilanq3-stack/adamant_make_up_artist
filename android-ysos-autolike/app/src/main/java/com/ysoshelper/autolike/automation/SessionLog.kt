package com.ysoshelper.autolike.automation

enum class LogAction { WOULD_LIKE, LIKE, NO_ACTION, STOP, ERROR }

data class LogEntry(
    val timestampMs: Long,
    val phase: SessionPhase,
    val fingerprint: String?,
    val action: LogAction,
    val reason: String,
    val count: Int,
    val limit: Int,
)

class SessionLog(private val maxEntries: Int = 500) {
    private val entries = ArrayDeque<LogEntry>()

    fun append(entry: LogEntry) {
        if (entries.size >= maxEntries) entries.removeFirst()
        entries.addLast(entry)
    }

    fun snapshot(): List<LogEntry> = entries.toList()

    fun asText(): String = buildString {
        appendLine("YSOS AutoLike session log")
        entries.forEach { e ->
            append(e.timestampMs).append('\t')
                .append(e.phase).append('\t')
                .append(e.action).append('\t')
                .append(e.count).append('/').append(e.limit).append('\t')
                .append(e.fingerprint.orEmpty()).append('\t')
                .appendLine(e.reason.replace('\n', ' '))
        }
    }

    fun clear() = entries.clear()
}
