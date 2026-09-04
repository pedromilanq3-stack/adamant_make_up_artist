"""Vida e morte: o risco real de perder um personagem.

Cada cérebro (psique ou mente) carrega `vida` (0..100), a saúde física. Ela cai com
acidente, doença, overdose, colapso, ferimento; sobe devagar com o tempo e com cuidado.
A cada lance do acaso, a cada dia que passa e a cada golpe físico, o Núcleo rola a morte.
Quem morre não volta: não existe comando de ressurreição.
"""

from __future__ import annotations

import random

RISCO_BASE = 0.002  # por lance, com tudo em ordem: raro, nunca zero


def _f(registro, chave: str, padrao: float = 0.0) -> float:
    try:
        return float(registro.get(chave, str(padrao)) or padrao)
    except (TypeError, ValueError):
        return padrao


def risco_por_vida(vida: float) -> tuple[float, list[str]]:
    if vida <= 0:
        return 1.0, ["vida 0: o corpo não aguentou"]
    fatores = []
    risco = 0.0
    if vida < 15:
        risco += 0.30
        fatores.append(f"vida {vida:g}: entre a vida e a morte")
    elif vida < 30:
        risco += 0.12
        fatores.append(f"vida {vida:g}: grave")
    elif vida < 50:
        risco += 0.04
        fatores.append(f"vida {vida:g}: debilitado")
    elif vida < 70:
        risco += 0.01
        fatores.append(f"vida {vida:g}: abaixo do normal")
    return risco, fatores


def risco_psique(estado: dict) -> tuple[float, list[str]]:
    """Probabilidade de morrer neste lance e os fatores que a compõem."""
    psique, saude = estado["psique"], estado["saude"]
    risco, fatores = risco_por_vida(_f(psique, "vida", 100))
    if risco >= 1.0:
        return 1.0, fatores
    risco += RISCO_BASE
    ativos = {t for t in ("dependencia", "depressao", "burnout", "insonia", "panico")
              if str(saude.get(f"{t}_estado", "")) == "ativo"}
    if "dependencia" in ativos:
        risco += 0.05 if "depressao" in ativos else 0.015
        fatores.append("dependência ativa" + (" junto com depressão" if "depressao" in ativos else ""))
    elif "depressao" in ativos:
        risco += 0.006
        fatores.append("depressão ativa")
    if {"burnout", "insonia"} <= ativos:
        risco += 0.01
        fatores.append("burnout e insônia juntos: o corpo não descansa")
    if _f(psique, "dor") >= 80:
        risco += 0.01
        fatores.append("dor acima de 80")
    if _f(psique, "energia") <= 10:
        risco += 0.01
        fatores.append("energia esgotada")
    if _f(psique, "odio") >= 80 and _f(psique, "impulso") >= 70:
        risco += 0.01
        fatores.append("ódio e impulso altos: se mete em briga")
    return min(1.0, risco), fatores


def risco_mente(mente) -> tuple[float, list[str]]:
    risco, fatores = risco_por_vida(_f(mente, "vida", 100))
    if risco >= 1.0:
        return 1.0, fatores
    risco += RISCO_BASE
    fase = str(mente.get("fase", ""))
    if fase == "CORINGA":
        risco += 0.04
        fatores.append("fase CORINGA: não se protege mais")
    elif fase == "LIMIAR":
        risco += 0.012
        fatores.append("fase LIMIAR: corre riscos que não correria")
    if _f(mente, "exaustao") >= 85:
        risco += 0.02
        fatores.append("exaustão acima de 85")
    if _f(mente, "exposicao_ao_caos") >= 85:
        risco += 0.02
        fatores.append("exposição ao caos acima de 85")
    return min(1.0, risco), fatores


def probabilidade_no_periodo(risco_por_lance: float, dias: int) -> float:
    """Cada dia é um lance pequeno: um décimo do risco que vem do estado, e quase nada do acaso puro."""
    if risco_por_lance >= 1.0:
        return 1.0
    do_estado = max(0.0, risco_por_lance - RISCO_BASE)
    diario = min(1.0, do_estado * 0.1 + RISCO_BASE * 0.005)
    return 1.0 - (1.0 - diario) ** max(0, dias)


def rolar(probabilidade: float, rng: random.Random | None = None) -> bool:
    if probabilidade >= 1.0:
        return True
    if probabilidade <= 0.0:
        return False
    return (rng or random).random() < probabilidade


def porcento(valor: float) -> str:
    return f"{valor * 100:.1f}%"
