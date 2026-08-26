package com.ysoshelper.autolike.automation

const val YSOS_PACKAGE = "br.com.esapiens.ysos"

data class SessionConfig(
    val limit: Int,
    val minDelayMs: Long,
    val maxDelayMs: Long,
    val dryRun: Boolean,
    val debug: Boolean,
) {
    companion object {
        fun defaults() = SessionConfig(
            limit = 50,
            minDelayMs = 3_000L,
            maxDelayMs = 7_000L,
            dryRun = true,
            debug = false,
        )
    }
}

sealed interface ConfigValidation {
    data object Valid : ConfigValidation
    data class Invalid(val message: String) : ConfigValidation
}

fun SessionConfig.validate(): ConfigValidation = when {
    limit !in 1..100 -> ConfigValidation.Invalid("Limit must be between 1 and 100")
    minDelayMs < 1_000L -> ConfigValidation.Invalid("Minimum delay must be at least 1 second")
    maxDelayMs < minDelayMs -> ConfigValidation.Invalid("Maximum delay must be >= minimum delay")
    else -> ConfigValidation.Valid
}

enum class SessionPhase {
    STOPPED,
    ARMED,
    WAITING_FOR_PROFILE,
    DELAYING,
    REVALIDATING,
    ACTING,
    WAITING_FOR_NEXT_PROFILE,
    DRY_RUN,
    COMPLETED,
    ERROR,
}

data class SessionStatus(
    val phase: SessionPhase = SessionPhase.STOPPED,
    val realLikes: Int = 0,
    val dryRunProcessed: Int = 0,
    val limit: Int = 50,
    val lastMessage: String = "Stopped",
)
