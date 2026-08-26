package com.ysoshelper.autolike.matching

import com.ysoshelper.autolike.accessibility.NodeRef
import com.ysoshelper.autolike.accessibility.UiSnapshot
import com.ysoshelper.autolike.accessibility.YsosSelectors
import com.ysoshelper.autolike.automation.YSOS_PACKAGE
import java.util.Locale

sealed interface LikeMatch {
    data object None : LikeMatch
    data class Unique(val target: NodeRef) : LikeMatch
    data class Ambiguous(val candidates: List<NodeRef>) : LikeMatch
}

class YsosUiMatcher {
    fun resolveLike(snapshot: UiSnapshot): LikeMatch {
        if (snapshot.packageName != YSOS_PACKAGE) return LikeMatch.None
        val actionable = snapshot.nodes.filter { it.enabled && it.clickable && !it.password }

        val idCandidates = actionable
            .filter { it.viewId != null && it.viewId in YsosSelectors.calibratedLikeViewIds }
            .map { it.ref }
            .distinctBy { it.path }
        if (idCandidates.isNotEmpty()) return result(idCandidates)

        val semantic = actionable.filter { node ->
            val desc = normalize(node.contentDescription)
            val text = normalize(node.text)
            desc in YsosSelectors.likeLabels || text in YsosSelectors.likeLabels
        }.map { it.ref }.distinctBy { it.path }

        return result(semantic)
    }

    private fun result(candidates: List<NodeRef>): LikeMatch = when (candidates.size) {
        0 -> LikeMatch.None
        1 -> LikeMatch.Unique(candidates.single())
        else -> LikeMatch.Ambiguous(candidates)
    }

    internal fun normalize(value: String?): String = value
        ?.trim()
        ?.lowercase(Locale.ROOT)
        ?.replace(Regex("\\s+"), " ")
        .orEmpty()
}
