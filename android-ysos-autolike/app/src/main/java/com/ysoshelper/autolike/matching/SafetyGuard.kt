package com.ysoshelper.autolike.matching

import com.ysoshelper.autolike.accessibility.UiSnapshot
import com.ysoshelper.autolike.accessibility.YsosSelectors
import com.ysoshelper.autolike.automation.YSOS_PACKAGE
import java.util.Locale

sealed interface SafetyDecision {
    data object Safe : SafetyDecision
    data class Stop(val reason: String) : SafetyDecision
}

class SafetyGuard {
    fun inspect(snapshot: UiSnapshot): SafetyDecision {
        if (snapshot.packageName != YSOS_PACKAGE) return SafetyDecision.Stop("YSOS is not foreground")
        val labels = snapshot.nodes.asSequence()
            .filter { !it.password }
            .flatMap { sequenceOf(it.text, it.contentDescription) }
            .filterNotNull()
            .map(::normalize)
            .filter { it.isNotBlank() }
        if (labels.any { visible -> YsosSelectors.verificationLabels.any { visible.contains(it) } }) {
            return SafetyDecision.Stop("Verification or security screen detected")
        }
        return SafetyDecision.Safe
    }

    private fun normalize(value: String): String = value
        .trim()
        .lowercase(Locale.ROOT)
        .replace(Regex("\\s+"), " ")
}
