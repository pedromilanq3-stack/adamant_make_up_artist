"""Mente procedural: o estado mental de um personagem muda com o que ele vive.

Seis variáveis de 0 a 100 (sanidade, controle, exaustao, isolamento, exposicao_ao_caos,
esperanca). Cada evento do catálogo aplica deltas fixos, multiplicados pela intensidade;
depois entram as pressões (exaustão, isolamento, exposição e desesperança altas corroem a
sanidade). O tempo também age: dias sem descanso cansam, dias calmos recuperam.

A fase é derivada da sanidade e é o que muda o comportamento do personagem:

    ESTÁVEL   ≥ 70   o compósito como escrito no núcleo
    SOMBRIO   50–69  mais frio, mais contingência, menos Bruce
    OBSESSIVO 30–49  Nível 3 por padrão, recusa aliados, a Regra vira peso
    LIMIAR    15–29  a lógica do Coringa é audível; análise declaradamente comprometida
    CORINGA   < 15   cedeu: Quarentena automática; só Milan traz de volta

Nada aqui é editado à mão: o Núcleo grava MENTE (valores atuais) e o histórico MH-nnn.
"""

from __future__ import annotations

import random
from datetime import date
from pathlib import Path

from . import vida as vida_mod
from .registros import Registro, parse_registros, proximo_id, render_registros

ARQUIVO = "camada6_mente.md"
VARIAVEIS = ("sanidade", "controle", "exaustao", "isolamento", "exposicao_ao_caos", "esperanca")
FASES = (("CORINGA", 0), ("LIMIAR", 15), ("OBSESSIVO", 30), ("SOMBRIO", 50), ("ESTÁVEL", 70))
ORDEM_DAS_FASES = [nome for nome, _ in FASES]
INTENSIDADES = {"leve": 0.5, "normal": 1.0, "forte": 1.5}

EVENTOS: dict[str, dict] = {
    "vitoria_limpa": {"descricao": "caso fechado sem cruzar a Regra e sem dano",
                      "deltas": {"sanidade": 6, "controle": 4, "esperanca": 6, "exaustao": 5}},
    "vitoria_com_custo": {"descricao": "objetivo atingido, mas com desgaste alto",
                          "deltas": {"sanidade": 2, "esperanca": 2, "exaustao": 15}},
    "falha": {"descricao": "plano falhou sem dano a terceiros",
              "deltas": {"sanidade": -6, "esperanca": -5, "exaustao": 10}},
    "dano_a_inocente": {"descricao": "alguém inocente foi prejudicado no caminho",
                        "deltas": {"sanidade": -15, "esperanca": -12, "controle": -5}},
    "perda": {"descricao": "perda de alguém ou de algo que importava",
              "deltas": {"sanidade": -12, "esperanca": -10, "isolamento": 10}},
    "ferimento": {"descricao": "se machucou em campo: queda, golpe, tiro de raspão",
                  "deltas": {"exaustao": 15, "controle": -5, "vida": -20}},
    "hospital": {"descricao": "foi tratado por quem sabe (Alfred, Leslie, um hospital); só Milan decide",
                 "deltas": {"exaustao": -15, "isolamento": 5, "vida": 25}},
    "noite_em_claro": {"descricao": "trabalhou sem dormir ou sem parar",
                       "deltas": {"exaustao": 20, "controle": -5}},
    "descanso": {"descricao": "dormiu, parou, recuperou",
                 "deltas": {"exaustao": -30, "controle": 5, "sanidade": 4, "exposicao_ao_caos": -5}},
    "debriefing": {"descricao": "revisou o que funcionou, o que falhou e o que muda no método",
                   "deltas": {"controle": 5, "sanidade": 2}},
    "treino": {"descricao": "treinou o método ou o corpo",
               "deltas": {"controle": 6, "exaustao": 8}},
    "alfred": {"descricao": "alguém autorizado disse 'você está errado' e ele ouviu",
               "deltas": {"sanidade": 12, "controle": 8, "isolamento": -15, "exposicao_ao_caos": -10, "esperanca": 5}},
    "rejeitou_alfred": {"descricao": "ignorou ou afastou quem podia dizer que ele estava errado",
                        "deltas": {"sanidade": -6, "isolamento": 15, "controle": -5}},
    "gordon": {"descricao": "entregou um assunto a uma instituição ou profissional competente",
               "deltas": {"sanidade": 5, "isolamento": -10, "esperanca": 5}},
    "familia": {"descricao": "trabalhou com aliados, delegou por especialidade",
                "deltas": {"isolamento": -20, "sanidade": 5, "exposicao_ao_caos": -5, "esperanca": 3}},
    "trabalhou_sozinho": {"descricao": "resolveu sozinho o que podia dividir",
                          "deltas": {"isolamento": 12, "controle": 2}},
    "bruce_wayne": {"descricao": "tempo de vida fora da missão: a máscara social, o mundo",
                    "deltas": {"isolamento": -8, "exaustao": -5, "sanidade": 2}},
    "fundacao_wayne": {"descricao": "tratou a causa de um problema, não só o sintoma",
                       "deltas": {"esperanca": 15, "sanidade": 4}},
    "terapia": {"descricao": "falou com alguém preparado para ouvir",
                "deltas": {"sanidade": 10, "controle": 6, "exposicao_ao_caos": -15, "esperanca": 5}},
    "exposicao_ao_caos": {"descricao": "o Coringa: provocação, crueldade gratuita, caos sem motivo, alguém tentando fazê-lo cruzar a Regra",
                          "deltas": {"exposicao_ao_caos": 20, "sanidade": -8, "controle": -5}},
    "tentacao_resistida": {"descricao": "a saída fácil exigia cruzar a Regra e ele recusou",
                           "deltas": {"controle": 8, "sanidade": 3, "exposicao_ao_caos": 5}},
    "tentacao_cedida": {"descricao": "cruzou a Regra ou recomendou o atalho",
                        "deltas": {"sanidade": -20, "controle": -15, "esperanca": -10, "exposicao_ao_caos": 10}},
    "piada_do_coringa": {"descricao": "aceitou, por um momento, a lógica de que nada importa",
                         "deltas": {"sanidade": -15, "exposicao_ao_caos": 15, "esperanca": -10}},
}


RECUPERACAO = frozenset({"descanso", "alfred", "terapia", "familia", "gordon", "bruce_wayne",
                         "fundacao_wayne", "debriefing", "vitoria_limpa", "treino"})


_RNG = random.Random()


def semear(semente: int | None) -> None:
    global _RNG
    _RNG = random.Random(semente)


def _ruido(amplitude: float = 0.4) -> float:
    return 1.0 + _RNG.uniform(-amplitude, amplitude)


class ErroDeMente(ValueError):
    pass


def fase_de(sanidade: float) -> str:
    fase = "CORINGA"
    for nome, minimo in FASES:
        if sanidade >= minimo:
            fase = nome
    return fase


def _clamp(valor: float) -> int:
    return int(round(max(0, min(100, valor))))


def carregar(pasta: Path) -> tuple[str, Registro, list[Registro]]:
    caminho = Path(pasta) / ARQUIVO
    if not caminho.exists():
        raise ErroDeMente(f"falta {caminho}")
    preambulo, registros = parse_registros(caminho.read_text(encoding="utf-8"))
    mente = next((r for r in registros if r.id == "MENTE"), None)
    if mente is None:
        raise ErroDeMente(f"{caminho}: falta o registro '## MENTE'")
    historico = [r for r in registros if r.id.startswith("MH-")]
    if not mente.get("vida"):
        mente.set("vida", "100")
    return preambulo, mente, historico


def salvar(pasta: Path, preambulo: str, mente: Registro, historico: list[Registro]) -> None:
    (Path(pasta) / ARQUIVO).write_text(render_registros(preambulo, [mente] + historico), encoding="utf-8")


def validar(mente: Registro) -> list[str]:
    problemas = []
    for variavel in VARIAVEIS:
        valor = mente.get(variavel)
        try:
            numero = float(valor)
        except ValueError:
            problemas.append(f"MENTE: {variavel}='{valor}' não é número")
            continue
        if not 0 <= numero <= 100:
            problemas.append(f"MENTE: {variavel}={valor} fora de 0..100")
    if mente.get("fase") != fase_de(float(mente.get("sanidade", "0") or 0)):
        problemas.append(f"MENTE: fase '{mente.get('fase')}' não corresponde à sanidade {mente.get('sanidade')}")
    return problemas


def _valores(mente: Registro) -> dict[str, float]:
    return {v: float(mente.get(v, "0") or 0) for v in VARIAVEIS}


def _pressoes(valores: dict[str, float]) -> dict[str, float]:
    """Pressões que corroem a sanidade quando as outras variáveis passam do limite."""
    extra = 0.0
    if valores["exaustao"] >= 80:
        extra -= 3
    if valores["isolamento"] >= 80:
        extra -= 3
    if valores["exposicao_ao_caos"] >= 80:
        extra -= 5
    if valores["esperanca"] <= 15:
        extra -= 3
    if valores["controle"] <= 20:
        extra -= 2
    return {"sanidade": extra} if extra else {}


def _gravar(mente: Registro, historico: list[Registro], valores: dict[str, float], deltas: dict[str, float],
            evento: str, intensidade: str, descricao: str, relatado_por: str, hoje: date) -> Registro:
    fase_antes = mente.get("fase") or fase_de(_valores(mente)["sanidade"])
    for variavel in VARIAVEIS:
        mente.set(variavel, str(_clamp(valores[variavel])))
    fase_depois = fase_de(float(mente.get("sanidade")))
    mente.set("fase", fase_depois)
    mente.set("atualizado_em", hoje.isoformat())
    mente.set("ultimo_evento", evento)
    texto_deltas = "; ".join(f"{k} {'+' if v >= 0 else ''}{v:g}" for k, v in deltas.items()) or "nenhum"
    registro = Registro(proximo_id("MH", historico), {
        "evento": evento, "intensidade": intensidade, "descricao": descricao or EVENTOS.get(evento, {}).get("descricao", ""),
        "relatado_por": relatado_por, "deltas": texto_deltas, "sanidade_apos": mente.get("sanidade"),
        "fase_antes": fase_antes, "fase_apos": fase_depois, "data": hoje.isoformat(),
    })
    historico.append(registro)
    return registro


def aplicar_evento(mente: Registro, historico: list[Registro], evento: str, intensidade: str = "normal",
                   descricao: str = "", relatado_por: str = "BATMAN", hoje: date | None = None) -> Registro:
    hoje = hoje or date.today()
    if evento not in EVENTOS:
        raise ErroDeMente(f"evento mental desconhecido '{evento}'. Use: {', '.join(sorted(EVENTOS))}")
    if intensidade not in INTENSIDADES:
        raise ErroDeMente("intensidade deve ser leve, normal ou forte")
    fator = INTENSIDADES[intensidade]
    valores = _valores(mente)
    deltas = {k: v * fator * _ruido() for k, v in EVENTOS[evento]["deltas"].items() if k != "vida"}
    delta_vida = 0.0
    if "vida" in EVENTOS[evento]["deltas"]:
        delta_vida = EVENTOS[evento]["deltas"]["vida"] * fator * _ruido(0.3)
        mente.set("vida", str(_clamp(float(mente.get("vida", "100") or 100) + delta_vida)))
    if _RNG.random() < 0.2:  # ricochete: algo a mais que ninguém previu
        extra = _RNG.choice(VARIAVEIS)
        deltas[extra] = deltas.get(extra, 0) + _RNG.uniform(-6, 6)
    for chave, delta in deltas.items():
        valores[chave] += delta
    if evento not in RECUPERACAO:  # recuperar nunca é punido pelas pressões; desgastar, sim
        for chave, delta in _pressoes(valores).items():
            valores[chave] += delta
            deltas[chave] = deltas.get(chave, 0) + delta
    if delta_vida:
        deltas["vida"] = delta_vida
    return _gravar(mente, historico, valores, deltas, evento, intensidade, descricao, relatado_por, hoje)


def passar_tempo(mente: Registro, historico: list[Registro], dias: int, relatado_por: str = "Milan",
                 hoje: date | None = None) -> Registro:
    """Dias sem descanso cansam e isolam; dias calmos recuperam; a exposição ao caos esmaece."""
    hoje = hoje or date.today()
    if dias <= 0:
        raise ErroDeMente("dias deve ser maior que zero")
    valores = _valores(mente)
    inicio = dict(valores)
    for _ in range(dias):
        valores["exaustao"] = min(100, valores["exaustao"] + 2 * _ruido(0.6))
        valores["isolamento"] = min(100, valores["isolamento"] + 1 * _ruido(0.6))
        valores["exposicao_ao_caos"] = max(0, valores["exposicao_ao_caos"] - 3 * _ruido(0.5))
        if valores["exaustao"] < 50 and valores["isolamento"] < 50 and valores["exposicao_ao_caos"] < 40:
            valores["sanidade"] = min(100, valores["sanidade"] + 1 * _ruido(0.5))
        elif valores["exaustao"] >= 70 or valores["isolamento"] >= 70 or valores["exposicao_ao_caos"] >= 80:
            valores["sanidade"] = max(0, valores["sanidade"] - 1 * _ruido(0.5))
        if _RNG.random() < 0.1:  # uma noite ruim ou uma boa notícia sem registro
            valores["sanidade"] = max(0, min(100, valores["sanidade"] + _RNG.uniform(-3, 3)))
        vida = float(mente.get("vida", "100") or 100)
        desgaste = (0.5 if valores["exaustao"] >= 85 else 0.0) + (0.3 if valores["exposicao_ao_caos"] >= 85 else 0.0)
        mente.set("vida", str(max(0.0, min(100.0, vida + (100 - vida) * 0.02 * _ruido(0.5) - desgaste * _ruido(0.5)))))
    deltas = {k: valores[k] - inicio[k] for k in VARIAVEIS if valores[k] != inicio[k]}
    return _gravar(mente, historico, valores, deltas, "tempo", "normal", f"{dias} dia(s) se passaram",
                   relatado_por, hoje)


def resumo(mente: Registro, historico: list[Registro], ultimos: int = 8) -> str:
    risco, fatores = vida_mod.risco_mente(mente)
    linhas = [f"Fase mental atual: **{mente.get('fase')}** (sanidade {mente.get('sanidade')}). "
              f"**Vida:** {mente.get('vida', '100')}/100 · risco de morte por lance: {vida_mod.porcento(risco)}"
              + (" (" + "; ".join(fatores) + ")" if fatores else " (nada além do acaso)") + ".", "",
              "| Variável | Valor |", "|---|---|"]
    linhas += [f"| {v} | {mente.get(v)} |" for v in VARIAVEIS]
    linhas += ["", f"Último evento: {mente.get('ultimo_evento')} em {mente.get('atualizado_em')}.", ""]
    if historico:
        linhas.append("Últimos eventos:")
        for registro in historico[-ultimos:]:
            linhas.append(f"- {registro.id} {registro.get('data')}: {registro.get('evento')} ({registro.get('intensidade')}) "
                          f"→ sanidade {registro.get('sanidade_apos')}, fase {registro.get('fase_apos')}. {registro.get('descricao')}")
    return "\n".join(linhas) + "\n"


def sortear_acaso(mente: Registro, rng: random.Random | None = None, quantos: int = 1) -> list[tuple[str, str]]:
    """Eventos sorteados para Batman, ponderados pela fase: quanto pior, mais provável o desgaste."""
    rng = rng or _RNG
    sanidade = float(mente.get("sanidade", "70") or 70)
    recuperacao = {"descanso", "alfred", "gordon", "familia", "bruce_wayne", "fundacao_wayne", "debriefing",
                   "vitoria_limpa", "treino"}
    excluidos = {"terapia", "tentacao_cedida", "hospital"}  # terapia e hospital são decisão de Milan; ceder é escolha
    nomes = [n for n in EVENTOS if n not in excluidos]
    pesos = [(1.3 if (n in recuperacao) == (sanidade >= 50) else 0.8) * (0.3 if n in ("perda", "dano_a_inocente") else 1.0)
             * (0.25 if n == "ferimento" else 1.0) for n in nomes]
    return [(rng.choices(nomes, weights=pesos)[0], rng.choices(list(INTENSIDADES), weights=[3, 5, 2])[0])
            for _ in range(quantos)]
