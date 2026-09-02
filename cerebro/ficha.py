"""Exporta o estado de um :class:`Brain` no formato de ficha da skill (0 a 10).

Assim um personagem criado pelo motor em código pode ser carregado pela skill
pura, com o mesmo ponto de partida.
"""

from __future__ import annotations

import time
from datetime import datetime

from .brain import Brain
from .emotions import EMOTION_LABELS, EMOTIONS
from .growth import VALUES
from .origin import level_label, parse_origin


FICHA_VALUE_NAMES: dict[str, str] = {
    "cuidado": "cuidado", "pertencimento": "pertencimento", "justica": "justiça", "verdade": "verdade",
    "lealdade": "lealdade", "conhecimento": "conhecimento", "liberdade": "liberdade", "seguranca": "segurança",
    "prazer": "prazer", "sobrevivencia": "sobrevivência", "poder": "poder", "vinganca": "vingança",
}


def _n(value: float, low: float = 0.0, high: float = 1.0) -> int:
    """Escala 0..1 (ou -1..1) para 0..10 (ou -10..10)."""
    if low < 0:
        return int(round(value * 10))
    return int(round((value - low) / (high - low) * 10))


def _date(stamp: float) -> str:
    return datetime.fromtimestamp(stamp).strftime("%d/%m/%Y %H:%M")


def render_ficha(brain: Brain, now: float | None = None) -> str:
    now = time.time() if now is None else now
    origin = parse_origin(brain.self_description)
    t, c, e, q = brain.traits.values, brain.character, brain.emotions.levels, brain.neuro.levels
    g = brain.neuro.genetics
    lines = [f"# Ficha de {brain.name}", "",
             "Escalas: 0 a 10 salvo indicação. Moralidade, vínculo e sorte vão de -10 a +10.", "",
             "## Identidade",
             f"- Nome: {brain.name} · Gênero dos adjetivos: {brain.gender}",
             f"- Descrição de origem (imutável): \"{origin.description}\"",
             f"- Nascimento: {_date(brain.born_at)} · Última conversa: {_date(brain.last_tick)}",
             f"- Experiências: {brain.experience_count} · Estágio: {brain._g(brain.stage)} · Plasticidade: {_n(brain.plasticity)}",
             ""]
    lines += ["## Origem (o que ele já traz ao nascer)",
              "- História: " + (" ".join(origin.history) or "(nenhuma além da descrição)"),
              "- Habilidades (nível): " + (" · ".join(f"{n} ({level_label(l)})" for n, l in brain.abilities.items()) or "(nenhuma declarada)"),
              "- Pessoas da minha vida: " + ("; ".join(f"{n} ({a})" if a else n for n, a in brain.relations.items()) or "(ninguém declarado)"),
              "- Medos: " + (", ".join(brain.fears) or "(nenhum declarado)"),
              "- Segredos (ele decide se, quando e para quem revela): " + ("; ".join(brain.secrets) or "(nenhum)"),
              ""]
    lines += ["## Consciência (o que sei e o que não sei)",
              "- Sei de mim: " + " ".join(brain.known),
              "- Ainda não sei: " + (" · ".join(brain.unknown) or "(nada que eu perceba)"),
              "- Descobri: " + ("; ".join(brain.discovered) or "(nada ainda)"),
              ""]
    lines += ["## Traços (fixos, mudam devagar)",
              f"abertura {_n(t['abertura'])} · conscienciosidade {_n(t['conscienciosidade'])} · extroversão {_n(t['extroversao'])} · amabilidade {_n(t['amabilidade'])} · neuroticismo {_n(t['neuroticismo'])}",
              "", "## Genética (fixa)",
              f"serotonina base {_n(g.production['serotonina'])} · dopamina base {_n(g.production['dopamina'])} · cortisol reatividade {_n(g.reactivity['cortisol'], 0.4, 2.0)} · gaba base {_n(g.production['gaba'])} · ocitocina base {_n(g.production['ocitocina'])} · ciclotimia {_n(g.cyclothymia)} · recuperação {_n(g.recovery, 0.4, 1.5)}",
              "", "## Emoções (agora)",
              " · ".join(f"{EMOTION_LABELS[k]} {_n(e[k])}" for k in EMOTIONS),
              f"Humor: {_n(brain.emotions.mood, -1)} · Energia: {_n(brain.emotions.energy)}",
              "", "## Química (agora)",
              " · ".join(f"{k} {_n(q[k])}" for k in ("dopamina", "serotonina", "noradrenalina", "cortisol", "ocitocina", "endorfina", "gaba")),
              f"Receptores de dopamina: {_n(brain.neuro.sensitivity['dopamina'], 0.3, 1.2)} · Picos de aprovação: {brain.neuro.reward_hits} · Fase do ciclo: {int(brain.neuro.cycle_phase / 6.2832 * 14)}/14",
              f"Quadros: {brain.neuro.describe_conditions() or 'nenhum'} · Episódios: {', '.join(f'{k} {v}x' for k, v in brain.neuro.episodes.items()) or 'nenhum'} · Sono: {brain.neuro.sleep_note() or 'descansado'}",
              "", "## Caráter",
              f"moralidade {_n(c.morality, -1)} · empatia {_n(c.empathy)} · confiança nos outros {_n(c.trust)} · coragem {_n(c.courage)} · honestidade {_n(c.honesty)} · agressividade {_n(c.aggression)}",
              "Trilha da moralidade: " + " ".join(str(_n(v, -1)) for v in c.history[-6:]),
              "", "## Relação com quem conversa",
              f"vínculo {_n(brain.bond, -1)} · resiliência {_n(brain.resilience)} · volatilidade {_n(brain.volatility)} · sorte {_n(brain.luck, -1)}",
              "", "## Valores (o que importa)",
              " · ".join(f"{FICHA_VALUE_NAMES[v]} {_n(brain.values.weights[v])}" for v in VALUES),
              "", "## Sentido",
              f"- Propósito: {brain.purpose}",
              "- Princípios: " + (" | ".join(brain.principles) or "(nenhum)"),
              "- Decisões: " + (" | ".join(brain.decisions) or "(nenhuma)"),
              "", "## Estratégias (postura: vezes, resultado médio -10..+10)",
              " · ".join(f"{s} {n}, {_n(brain.strategies.reward[s], -1)}" for s, n in brain.strategies.tries.items()),
              "", "## Memória"]
    short = brain.memory.short_term
    long = sorted(brain.memory.long_term, key=lambda m: m.when)
    lines.append("- Curto prazo (até 7): " + ("; ".join(f"\"{m.text}\" ({EMOTION_LABELS.get(m.emotion, m.emotion) or 'neutro'}, {_n(m.valence, -1):+d})" for m in short) or "(vazia)"))
    lines.append("- Longo prazo (força 1-10): " + ("; ".join(f"\"{m.text}\" (força {max(1, _n(m.strength))}, {_n(m.valence, -1):+d}{', passado' if 'passado' in m.tags else ''})" for m in long) or "(vazia)"))
    lines.append("- Lições: " + ("; ".join(l.text for l in brain.memory.lessons) or "(nenhuma)"))
    lines.append("- O que a vida fez: " + ("; ".join(brain.world_log) or "(nada ainda)"))
    lines += ["", "## Turno",
              f"- Postura atual: {brain.stance}",
              f"- Impulso: {brain.whim or 'nenhum'}",
              "- Última resposta dada: (nenhuma)",
              f"- Narrativa: \"{brain.narrative[-1]}\"", ""]
    return "\n".join(lines)
