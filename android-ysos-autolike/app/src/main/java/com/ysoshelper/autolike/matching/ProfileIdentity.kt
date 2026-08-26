package com.ysoshelper.autolike.matching

import com.ysoshelper.autolike.accessibility.NodeRef
import com.ysoshelper.autolike.accessibility.UiSnapshot
import com.ysoshelper.autolike.accessibility.YsosSelectors
import java.security.MessageDigest
import java.util.Locale

class ProfileIdentity {
    fun fingerprint(snapshot: UiSnapshot, likeTarget: NodeRef): String {
        val eligible = snapshot.nodes
            .asSequence()
            .filter { !it.password && it.ref.path != likeTarget.path }
            .filterNot { node ->
                normalize(node.text) in YsosSelectors.likeLabels ||
                    normalize(node.contentDescription) in YsosSelectors.likeLabels
            }
            .sortedWith(compareBy({ it.ref.path.size }, { it.ref.path.joinToString("/") }))
            .toList()

        val textNodes = eligible.mapNotNull { node ->
            val label = node.text ?: node.contentDescription
            label?.takeIf { it.isNotBlank() }?.take(80)?.let { node.ref.path to it }
        }.take(12).toMap()

        val material = buildString {
            append(snapshot.packageName).append('\n')
            eligible.forEach { node ->
                append(node.ref.path.joinToString("/"))
                    .append('|').append(node.className.orEmpty())
                    .append('|').append(node.viewId.orEmpty())
                    .append('|').append(textNodes[node.ref.path].orEmpty())
                    .append('\n')
            }
        }
        val digest = MessageDigest.getInstance("SHA-256").digest(material.toByteArray(Charsets.UTF_8))
        return digest.take(16).joinToString("") { "%02x".format(it) }
    }

    private fun normalize(value: String?): String = value
        ?.trim()
        ?.lowercase(Locale.ROOT)
        ?.replace(Regex("\\s+"), " ")
        .orEmpty()
}
