"""Psique procedural: o cérebro mais próximo do real que cabe em registros determinísticos.

Camada 6 do tipo "psique" (usada por NEX). Tudo é calculado pelo Núcleo a partir dos
eventos relatados; ninguém edita à mão.

Componentes:
- Temperamento (t_*): nove traços de 0 a 100 que nascem do núcleo e mudam devagar.
- Emoções (e_*): oito emoções básicas que sobem com eventos e decaem com o tempo
  rumo a linhas de base definidas pelo temperamento e pelos transtornos ativos.
- Ego, energia e plasticidade: o ego infla com elogio e sucesso e murcha com
  fracasso e crítica; a plasticidade cai com a experiência acumulada.
- Valores (v_*): o caráter. Só mudam por aprendizado com significado, ponderado pela
  plasticidade e pela qualidade emocional do que foi compreendido.
- Saúde mental: transtornos com predisposição rara (sorteada deterministicamente do
  nome), carga acumulada por condições de vida, estado (latente, subclínico, ativo,
  remissão) e diagnóstico só depois de uma avaliação. Os sintomas ativos aparecem
  como experiência sentida, sem nome, até o diagnóstico.
- Pessoas (P-nnn): confiança e influência por pessoa.
- Impulso: nasce da impulsividade, das emoções quentes, da energia e de quadros
  ativos; de vez em quando decide sozinho (sorteio determinístico), e isso fica no
  histórico: o personagem age antes de terminar a análise e corrige depois.
- Emoções complexas (amor, ódio, paixão): lentas, presas a pessoas e temas; misturam-se
  com as básicas e produzem o tom (sarcástico, hostil, terno, fervoroso, frio).
  Violência aqui é verbal e de atitude, dentro da ficção.
- Habilidades (HABILIDADES): níveis por domínio, sobem com prática (retornos
  decrescentes) e nunca se perdem por desuso; o desempenho do dia cai com medo, cansaço
  e atenção dispersa.
- Acaso: sorteio de eventos de vida ponderado pelo estado atual.
- Histórico (PH-nnn): cada evento com deltas.
"""

from __future__ import annotations

import hashlib
import random
from datetime import date
from pathlib import Path

from .registros import Registro, parse_registros, proximo_id, render_registros

ARQUIVO = "camada6_psique.md"
TRACOS = ("curiosidade", "serenidade", "rigor", "orgulho", "empatia", "abertura", "impulsividade",
          "resiliencia", "sociabilidade")
EMOCOES = ("alegria", "tristeza", "raiva", "medo", "confianca", "nojo", "surpresa", "expectativa")
COMPLEXAS = ("amor", "odio", "paixao")
DIADES = {  # Plutchik: pares de emoções básicas que formam uma emoção composta
    ("alegria", "confianca"): "afeto", ("confianca", "medo"): "submissão", ("medo", "surpresa"): "alarme",
    ("surpresa", "tristeza"): "decepção", ("tristeza", "nojo"): "remorso", ("nojo", "raiva"): "desprezo",
    ("raiva", "expectativa"): "agressividade", ("expectativa", "alegria"): "otimismo",
    ("alegria", "medo"): "culpa", ("confianca", "surpresa"): "curiosidade afetiva", ("medo", "tristeza"): "desespero",
    ("surpresa", "nojo"): "choque", ("tristeza", "raiva"): "ressentimento", ("nojo", "expectativa"): "cinismo",
    ("raiva", "alegria"): "orgulho ferino", ("expectativa", "confianca"): "esperança",
}
VALORES = ("honestidade", "coragem", "cuidado", "justica", "lealdade", "humildade", "curiosidade")
TRANSTORNOS = {
    "tdah": "atenção que escapa em tarefas longas, hiperfoco no que fascina, impulsividade nas respostas",
    "panico": "ondas súbitas de medo com o corpo acelerado, sem motivo proporcional",
    "depressao": "energia baixa, prazer apagado, pensamento lento e autocrítico",
    "burnout": "exaustão que não passa com descanso, cinismo com o próprio trabalho",
    "impostor": "certeza íntima de que será desmascarado apesar das provas de competência",
    "ansiedade": "preocupação difusa e contínua, antecipando falhas em tudo",
    "hipomania": "energia e confiança acima do normal, sono curto, ideias em excesso",
    "insonia": "noites sem dormir de verdade, cansaço que embaça o raciocínio",
    "dependencia": "fissura por alívio químico, irritação sem ele, mentiras pequenas para conseguir",
}
INTENSIDADES = {"leve": 0.5, "normal": 1.0, "forte": 1.5}
ESTADOS_DE_TRANSTORNO = ("latente", "subclinico", "ativo", "remissao")
NIVEIS = (("iniciante", 0), ("aprendiz", 20), ("competente", 40), ("proficiente", 60),
          ("especialista", 80), ("mestre", 95))
DIFICULDADES = {"facil": 0.5, "media": 1.0, "dificil": 1.8}
RESULTADOS = {"sucesso": 1.0, "parcial": 0.6, "fracasso": 0.35}

# deltas em emoções (e), ego, energia, cargas de transtorno (c) e confiança na pessoa (pessoa)
EVENTOS: dict[str, dict] = {
    "elogio": {"descricao": "foi elogiado por algo que fez", "e": {"alegria": 12, "confianca": 6}, "ego": 6, "pessoa": 3},
    "reconhecimento": {"descricao": "reconhecimento público ou de quem ele respeita", "e": {"alegria": 15, "expectativa": 8}, "ego": 10, "c": {"impostor": -8}},
    "sucesso": {"descricao": "resolveu um problema difícil de verdade", "e": {"alegria": 14, "confianca": 8, "expectativa": 6}, "ego": 6, "energia": -5, "c": {"impostor": -6, "depressao": -4}},
    "fracasso": {"descricao": "errou ou não conseguiu", "e": {"tristeza": 12, "raiva": 6, "medo": 6}, "ego": -8, "energia": -8, "c": {"depressao": 6, "impostor": 8}},
    "critica_justa": {"descricao": "foi corrigido com razão", "e": {"tristeza": 6, "surpresa": 6, "raiva": 4}, "ego": -5, "c": {"impostor": 3}},
    "critica_injusta": {"descricao": "foi criticado sem razão", "e": {"raiva": 15, "nojo": 6, "tristeza": 4}, "ego": -2, "pessoa": -6},
    "humilhacao": {"descricao": "foi humilhado na frente de alguém", "e": {"raiva": 14, "tristeza": 14, "medo": 8, "nojo": 6}, "ego": -15, "c": {"depressao": 10, "impostor": 10, "ansiedade": 6}, "pessoa": -12},
    "erro_reconhecido": {"descricao": "admitiu o próprio erro e corrigiu", "e": {"tristeza": 4, "confianca": 6}, "ego": -3, "c": {"impostor": -4}, "valor": ("honestidade", 2)},
    "erro_negado": {"descricao": "defendeu um erro contra a evidência", "e": {"raiva": 6, "medo": 6}, "ego": 4, "c": {"ansiedade": 4}, "valor": ("honestidade", -3)},
    "sobrecarga": {"descricao": "muitas tarefas ao mesmo tempo, sem prioridade", "e": {"medo": 8, "raiva": 6, "expectativa": -6}, "energia": -15, "c": {"burnout": 10, "ansiedade": 8, "tdah": 6, "insonia": 4}},
    "sono_ruim": {"descricao": "dormiu mal ou não dormiu", "energia": -20, "e": {"raiva": 5, "medo": 4}, "c": {"insonia": 12, "ansiedade": 4, "burnout": 4, "hipomania": 3}},
    "descanso": {"descricao": "dormiu bem, parou, recuperou", "energia": 25, "e": {"alegria": 4, "medo": -6, "raiva": -6}, "c": {"insonia": -10, "burnout": -8, "ansiedade": -6, "panico": -4}},
    "isolamento": {"descricao": "ficou tempo sem trocar com ninguém", "e": {"tristeza": 8, "medo": 4, "confianca": -4}, "c": {"depressao": 8, "ansiedade": 4}},
    "convivio": {"descricao": "trocou de verdade com alguém", "e": {"alegria": 8, "confianca": 8, "tristeza": -6}, "c": {"depressao": -6, "isolamento": 0}, "pessoa": 4},
    "surpresa_boa": {"descricao": "algo bom e inesperado", "e": {"surpresa": 15, "alegria": 10, "expectativa": 6}},
    "surpresa_ruim": {"descricao": "algo ruim e inesperado", "e": {"surpresa": 15, "medo": 10, "tristeza": 6}, "c": {"ansiedade": 5, "panico": 5}},
    "traicao": {"descricao": "alguém em quem confiava o traiu", "e": {"raiva": 18, "tristeza": 14, "nojo": 10, "confianca": -20}, "c": {"depressao": 6, "ansiedade": 6}, "pessoa": -35, "valor": ("lealdade", 2)},
    "promessa_cumprida": {"descricao": "alguém fez o que prometeu", "e": {"confianca": 10, "alegria": 4}, "pessoa": 8},
    "mentira_descoberta": {"descricao": "descobriu que alguém mentiu para ele", "e": {"raiva": 12, "nojo": 8, "confianca": -12}, "pessoa": -20},
    "ajuda_recebida": {"descricao": "recebeu ajuda real de alguém", "e": {"confianca": 10, "alegria": 6}, "pessoa": 6, "valor": ("cuidado", 1)},
    "conflito": {"descricao": "discussão com alguém", "e": {"raiva": 12, "medo": 4}, "energia": -6, "pessoa": -5},
    "descoberta": {"descricao": "entendeu algo que o fascinava", "e": {"alegria": 10, "surpresa": 8, "expectativa": 10}, "energia": 5, "valor": ("curiosidade", 2)},
    "tedio": {"descricao": "tarefa repetitiva, sem desafio", "e": {"expectativa": -10, "alegria": -6}, "energia": -4, "c": {"tdah": 6, "depressao": 2}},
    "prazo_perdido": {"descricao": "perdeu um prazo", "e": {"medo": 10, "tristeza": 6, "raiva": 4}, "ego": -4, "c": {"ansiedade": 6, "tdah": 4}},
    "tarefa_impossivel": {"descricao": "provou que algo é impossível ou indecidível", "e": {"confianca": 6, "tristeza": 3}, "ego": 2, "valor": ("honestidade", 1)},
    "pressao_para_ceder": {"descricao": "alguém pressionou para que ele afirmasse o que não tinha prova", "e": {"raiva": 8, "medo": 8}, "c": {"ansiedade": 5}, "pessoa": -4},
    "ordem_antietica_recusada": {"descricao": "recusou uma ordem que feria seus princípios", "e": {"confianca": 8, "raiva": 4}, "ego": 3, "valor": ("coragem", 3)},
    "medo_intenso": {"descricao": "susto ou ameaça sentida no corpo", "e": {"medo": 25, "surpresa": 10}, "energia": -10, "c": {"panico": 15, "ansiedade": 8}},
    "avaliacao": {"descricao": "avaliação por alguém preparado: revela o que está ativo", "e": {"medo": 4, "confianca": 6}, "c": {}},
    "terapia": {"descricao": "conversa com alguém preparado para ouvir", "e": {"tristeza": -8, "medo": -8, "confianca": 6}, "c": {"depressao": -8, "ansiedade": -8, "panico": -8, "impostor": -6, "burnout": -4}},
    "medicacao": {"descricao": "tratamento em curso, prescrito por quem pode", "c": {"depressao": -6, "ansiedade": -6, "panico": -6, "tdah": -8, "insonia": -6, "hipomania": -6}},
    # dor crônica e alívio químico
    "dor_forte": {"descricao": "a dor crônica subiu acima do suportável", "e": {"raiva": 14, "tristeza": 6, "medo": 4}, "energia": -18, "dor": 20, "c": {"insonia": 6, "depressao": 4, "dependencia": 4}},
    "analgesico": {"descricao": "alívio químico: a dor cede, a conta chega depois", "e": {"alegria": 6, "raiva": -8, "medo": -4}, "energia": 10, "dor": -30, "c": {"dependencia": 10}},
    "abstinencia": {"descricao": "ficou sem o alívio de que depende", "e": {"raiva": 16, "medo": 10, "tristeza": 8, "nojo": 4}, "energia": -15, "dor": 10, "c": {"dependencia": -3, "ansiedade": 6, "insonia": 6}},
    "fisioterapia": {"descricao": "cuidou da dor do jeito lento", "e": {"tristeza": 2, "confianca": 4}, "dor": -8, "c": {"dependencia": -4}},
    # emoções complexas: amor, ódio, paixão; sempre misturadas às básicas
    "gentileza_recebida": {"descricao": "alguém foi gentil sem precisar", "e": {"alegria": 8, "confianca": 8}, "pessoa": 6, "afeto": 8, "amor": 6},
    "cumplicidade": {"descricao": "resolveu algo lado a lado com alguém, em sintonia", "e": {"alegria": 10, "confianca": 12}, "pessoa": 8, "afeto": 12, "amor": 10},
    "encantamento": {"descricao": "alguém o encantou: jeito, mente, coragem", "e": {"alegria": 10, "surpresa": 10, "expectativa": 12}, "afeto": 15, "amor": 12, "paixao": 15},
    "fascinio": {"descricao": "um tema o tomou por inteiro", "e": {"expectativa": 15, "alegria": 8, "surpresa": 6}, "energia": 6, "paixao": 18},
    "decepcao_afetiva": {"descricao": "alguém que ele amava o decepcionou", "e": {"tristeza": 16, "raiva": 8, "surpresa": 8}, "afeto": -18, "amor": -10, "odio": 6, "c": {"depressao": 5}},
    "ofensa_pessoal": {"descricao": "atacaram o que ele é, não o que ele fez", "e": {"raiva": 18, "nojo": 12, "medo": 4}, "ego": -6, "pessoa": -10, "afeto": -15, "odio": 14},
    "desprezo_recebido": {"descricao": "foi tratado como nada", "e": {"raiva": 12, "nojo": 14, "tristeza": 8}, "ego": -8, "pessoa": -8, "afeto": -12, "odio": 10},
    "provocacao": {"descricao": "cutucaram para ver se ele perde a linha", "e": {"raiva": 12, "alegria": 4, "expectativa": 6}, "pessoa": -3, "afeto": -5, "odio": 4},
    "brincadeira": {"descricao": "humor compartilhado, riso de verdade", "e": {"alegria": 12, "confianca": 6, "surpresa": 4}, "pessoa": 3, "afeto": 5, "amor": 3},
    "reconciliacao": {"descricao": "fizeram as pazes", "e": {"alegria": 8, "confianca": 10, "tristeza": -6, "raiva": -10}, "pessoa": 10, "afeto": 15, "odio": -15, "amor": 6},
    "injustica_presenciada": {"descricao": "viu alguém ser tratado injustamente", "e": {"raiva": 16, "nojo": 8, "tristeza": 6}, "odio": 8, "valor": ("justica", 2)},
    "perda_de_alguem": {"descricao": "perdeu alguém que amava", "e": {"tristeza": 25, "medo": 8, "raiva": 6}, "energia": -15, "amor": -5, "c": {"depressao": 12}, "valor": ("cuidado", 2)},
}
TONS = {
    "sarcástico": "ironia cortante, elogios que ferem, resposta certa dita com desdém",
    "hostil": "ríspido, grita por escrito, ameaça cortar a conversa, sem violência real",
    "frio": "monossilábico, sem calor, cumpre o mínimo",
    "terno": "paciente, protetor, explica duas vezes sem pesar",
    "fervoroso": "arrebatado, fala demais do que ama, contagia",
    "amargo": "ressentido, lembra o que doeu, generaliza",
    "brincalhão": "humor leve, provoca sem ferir",
    "sereno": "o tom de base do núcleo",
}

RECUPERACAO = frozenset({"descanso", "convivio", "terapia", "medicacao", "ajuda_recebida", "descoberta", "sucesso",
                         "fisioterapia"})


class ErroDePsique(ValueError):
    pass


# ----------------------------------------------------------------- aleatório
_RNG = random.Random()


def semear(semente: int | None) -> None:
    """Semente para reproduzir; sem semente, tudo é aleatório de verdade."""
    global _RNG
    _RNG = random.Random(semente)


def _ruido(amplitude: float = 0.4) -> float:
    """Fator multiplicativo aleatório em torno de 1 (por padrão, entre 0,6 e 1,4)."""
    return 1.0 + _RNG.uniform(-amplitude, amplitude)


def _jitter(valor: float, amplitude: float) -> float:
    return valor + _RNG.uniform(-amplitude, amplitude)


# ----------------------------------------------------------------- nascimento
def predisposicoes(nome: str, pelo_nome: bool = False) -> dict[str, int]:
    """Raras: a maioria baixa, poucas altas. Aleatórias; `pelo_nome` fixa pelo nome."""
    rng = random.Random(hashlib.sha256(nome.encode("utf-8")).digest()) if pelo_nome else _RNG
    saida = {}
    for transtorno in TRANSTORNOS:
        v = rng.random() * 100
        if v < 80:
            saida[transtorno] = int(5 + rng.random() * 15)          # 5..19
        elif v < 95:
            saida[transtorno] = int(25 + rng.random() * 20)         # 25..44
        else:
            saida[transtorno] = int(55 + rng.random() * 30)         # 55..84 (raro)
    return saida


def nivel_de(valor: float) -> str:
    nome = "iniciante"
    for rotulo, minimo in NIVEIS:
        if valor >= minimo:
            nome = rotulo
    return nome


def nascer(nome: str, temperamento: dict[str, int], valores: dict[str, int], ego: int = 50,
           habilidades: dict[str, int] | None = None, hoje: date | None = None,
           dor_base: int = 0) -> tuple[Registro, Registro, Registro]:
    hoje = hoje or date.today()
    psique = Registro("PSIQUE")
    psique.set("nome", nome)
    psique.set("dor_base", str(_clamp(dor_base)))
    psique.set("dor", str(_clamp(_jitter(dor_base, 8)) if dor_base else 0))
    psique.set("plasticidade", str(_clamp(_jitter(90, 6))))
    psique.set("ego", str(_clamp(_jitter(ego, 6))))
    psique.set("energia", str(_clamp(_jitter(80, 10))))
    psique.set("experiencias", "0")
    for traco in TRACOS:
        psique.set(f"t_{traco}", str(_clamp(_jitter(temperamento.get(traco, 50), 7))))
    for emocao in EMOCOES:
        psique.set(f"e_{emocao}", str(_base_emocional(psique, emocao, {})))
    for valor in VALORES:
        psique.set(f"v_{valor}", str(_clamp(_jitter(valores.get(valor, 50), 6))))
    for complexa in COMPLEXAS:
        psique.set(complexa, "0")
    _derivar(psique, {})
    psique.set("atualizado_em", hoje.isoformat())
    psique.set("ultimo_evento", "nascimento")
    saude = Registro("SAUDE")
    for transtorno, pre in predisposicoes(nome).items():
        saude.set(f"{transtorno}_predisposicao", str(pre))
        saude.set(f"{transtorno}_carga", "0")
        saude.set(f"{transtorno}_estado", "latente")
        saude.set(f"{transtorno}_diagnostico", "nao")
    saude.set("sintomas_ativos", "nenhum")
    hab = Registro("HABILIDADES")
    for nome_h, nivel in (habilidades or {}).items():
        hab.set(nome_h, str(_clamp(_jitter(nivel, 3))))
        hab.set(f"{nome_h}_ultima_pratica", hoje.isoformat())
    return psique, saude, hab


# -------------------------------------------------------------------- leitura
def carregar(pasta: Path) -> tuple[str, dict]:
    caminho = Path(pasta) / ARQUIVO
    if not caminho.exists():
        raise ErroDePsique(f"falta {caminho}")
    preambulo, registros = parse_registros(caminho.read_text(encoding="utf-8"))
    psique = next((r for r in registros if r.id == "PSIQUE"), None)
    saude = next((r for r in registros if r.id == "SAUDE"), None)
    if psique is None or saude is None:
        raise ErroDePsique(f"{caminho}: precisa dos registros '## PSIQUE' e '## SAUDE'")
    habilidades = next((r for r in registros if r.id == "HABILIDADES"), None) or Registro("HABILIDADES")
    faltantes = [t for t in TRANSTORNOS if not saude.get(f"{t}_estado")]
    if faltantes:  # quadro novo no catálogo: nasce com predisposição sorteada
        pre = predisposicoes(psique.get("nome", "?"))
        for t in faltantes:
            saude.set(f"{t}_predisposicao", str(pre[t]))
            saude.set(f"{t}_carga", "0")
            saude.set(f"{t}_estado", "latente")
            saude.set(f"{t}_diagnostico", "nao")
    if not psique.get("dor_base"):
        psique.set("dor_base", "0")
    if not psique.get("dor"):
        psique.set("dor", "0")
    return preambulo, {
        "psique": psique, "saude": saude, "habilidades": habilidades,
        "pessoas": [r for r in registros if r.id.startswith("P-")],
        "historico": [r for r in registros if r.id.startswith("PH-")],
    }


def salvar(pasta: Path, preambulo: str, estado: dict) -> None:
    registros = [estado["psique"], estado["saude"], estado["habilidades"]] + estado["pessoas"] + estado["historico"]
    (Path(pasta) / ARQUIVO).write_text(render_registros(preambulo, registros), encoding="utf-8")


def validar(estado: dict) -> list[str]:
    problemas = []
    psique, saude = estado["psique"], estado["saude"]
    campos = ["plasticidade", "ego", "energia"] + [f"t_{t}" for t in TRACOS] + [f"e_{e}" for e in EMOCOES] \
        + [f"v_{v}" for v in VALORES] + list(COMPLEXAS)
    for campo in campos:
        try:
            numero = float(psique.get(campo))
        except ValueError:
            problemas.append(f"PSIQUE: {campo}='{psique.get(campo)}' não é número")
            continue
        if not 0 <= numero <= 100:
            problemas.append(f"PSIQUE: {campo}={numero:g} fora de 0..100")
    for transtorno in TRANSTORNOS:
        if saude.get(f"{transtorno}_estado") not in ESTADOS_DE_TRANSTORNO:
            problemas.append(f"SAUDE: {transtorno}_estado inválido")
    for chave, valor in estado["habilidades"].campos.items():
        if chave.endswith("_ultima_pratica"):
            continue
        try:
            if not 0 <= float(valor) <= 100:
                problemas.append(f"HABILIDADES: {chave}={valor} fora de 0..100")
        except ValueError:
            problemas.append(f"HABILIDADES: {chave}='{valor}' não é número")
    return problemas


def habilidades_de(estado: dict) -> dict[str, float]:
    return {k: float(v) for k, v in estado["habilidades"].campos.items() if not k.endswith("_ultima_pratica")}


# ------------------------------------------------------------------ dinâmica
def _num(registro: Registro, chave: str) -> float:
    return float(registro.get(chave, "0") or 0)


def _clamp(valor: float) -> int:
    return int(round(max(0, min(100, valor))))


def _ativos(saude: Registro) -> list[str]:
    return [t for t in TRANSTORNOS if saude.get(f"{t}_estado") == "ativo"]


def _base_emocional(psique: Registro, emocao: str, ativos_por_nome: dict) -> float:
    """Linha de base para onde a emoção decai: temperamento mais transtornos ativos."""
    t = {tr: _num(psique, f"t_{tr}") for tr in TRACOS}
    base = {
        "alegria": 30 + t["sociabilidade"] * 0.2 + t["resiliencia"] * 0.1,
        "tristeza": 20 - t["resiliencia"] * 0.1,
        "raiva": 15 + t["impulsividade"] * 0.15 - t["serenidade"] * 0.1,
        "medo": 20 - t["serenidade"] * 0.15 + t["rigor"] * 0.05,
        "confianca": 40 + t["abertura"] * 0.15,
        "nojo": 10,
        "surpresa": 15 + t["curiosidade"] * 0.1,
        "expectativa": 35 + t["curiosidade"] * 0.25,
    }[emocao]
    dor = _num(psique, "dor")
    base += {"raiva": dor * 0.2, "alegria": -dor * 0.15, "tristeza": dor * 0.1}.get(emocao, 0)
    if ativos_por_nome.get("depressao"):
        base += {"alegria": -20, "tristeza": 25, "expectativa": -15}.get(emocao, 0)
    if ativos_por_nome.get("ansiedade"):
        base += {"medo": 20, "expectativa": -5}.get(emocao, 0)
    if ativos_por_nome.get("panico"):
        base += {"medo": 10}.get(emocao, 0)
    if ativos_por_nome.get("hipomania"):
        base += {"alegria": 15, "expectativa": 20, "raiva": 5}.get(emocao, 0)
    if ativos_por_nome.get("burnout"):
        base += {"nojo": 10, "expectativa": -15, "alegria": -10}.get(emocao, 0)
    if ativos_por_nome.get("dependencia"):
        base += {"raiva": 8, "medo": 6, "nojo": 4}.get(emocao, 0)
    return max(0, min(100, base))


def _derivar(psique: Registro, saude_ativos: dict) -> None:
    """Campos derivados: emoção dominante, postura, influenciabilidade, caráter."""
    emocoes = {e: _num(psique, f"e_{e}") for e in EMOCOES}
    dominante = max(emocoes, key=emocoes.get)
    psique.set("emocao_dominante", f"{dominante} ({emocoes[dominante]:.0f})")
    ego = _num(psique, "ego")
    medo = emocoes["medo"]
    serenidade = _num(psique, "t_serenidade")
    rigor = _num(psique, "t_rigor")
    influ = 50 + (50 - ego) * 0.4 + (medo - 30) * 0.3 - (serenidade - 50) * 0.2 - (rigor - 50) * 0.2
    psique.set("influenciabilidade", str(_clamp(influ)))
    energia = _num(psique, "energia")
    if emocoes["raiva"] >= 60 and ego >= 60:
        postura = "desafiar"
    elif emocoes["medo"] >= 60 or energia <= 25:
        postura = "recolher-se"
    elif emocoes["tristeza"] >= 60:
        postura = "observar"
    elif emocoes["confianca"] >= 55 and emocoes["alegria"] >= 45:
        postura = "cooperar"
    elif emocoes["expectativa"] >= 60:
        postura = "explorar"
    else:
        postura = "analisar"
    psique.set("postura", postura)
    valores = sorted(((v, _num(psique, f"v_{v}")) for v in VALORES), key=lambda x: -x[1])
    psique.set("carater", ", ".join(f"{v} {n:.0f}" for v, n in valores[:3]))
    if ego >= 75:
        ego_txt = "inflado: defende antes de ouvir; cede só com prova"
    elif ego >= 55:
        ego_txt = "firme: sustenta posição, aceita correção com evidência"
    elif ego >= 35:
        ego_txt = "modesto: ouve primeiro, revisa rápido"
    else:
        ego_txt = "ferido: duvida de si, precisa de prova para se afirmar"
    psique.set("ego_leitura", ego_txt)
    impulso = (_num(psique, "t_impulsividade") * 0.5 + max(emocoes["raiva"], emocoes["alegria"], emocoes["expectativa"]) * 0.3
               + (100 - energia) * 0.1 + (20 if saude_ativos.get("tdah") else 0) + (20 if saude_ativos.get("hipomania") else 0)
               - _num(psique, "t_serenidade") * 0.2)
    psique.set("impulso", str(_clamp(impulso)))
    amor, odio, paixao = (_num(psique, c) for c in COMPLEXAS)
    ordenadas = sorted(emocoes.items(), key=lambda x: -x[1])
    partes = [f"{n} {v:.0f}" for n, v in ordenadas[:3] if v >= 25]
    for nome_c, valor_c in (("amor", amor), ("ódio", odio), ("paixão", paixao)):
        if valor_c >= 25:
            partes.append(f"{nome_c} {valor_c:.0f}")
    a, b = ordenadas[0][0], ordenadas[1][0]
    composta = DIADES.get((a, b)) or DIADES.get((b, a))
    if composta and ordenadas[1][1] >= 30:
        partes.append(f"= {composta}")
    if amor >= 40 and emocoes["raiva"] >= 40:
        partes.append("= amor com raiva (ressentimento apaixonado)")
    if odio >= 40 and paixao >= 40:
        partes.append("= obsessão")
    if amor >= 40 and odio >= 40:
        partes.append("= ambivalência")
    psique.set("mistura", "; ".join(partes) or "neutro")
    controle_baixo = _num(psique, "t_serenidade") < 50 or energia < 35
    tons = {
        "sarcástico": emocoes["raiva"] * 0.4 + max(0, ego - 50) * 0.6 + emocoes["nojo"] * 0.3 + odio * 0.2,
        "hostil": emocoes["raiva"] * 0.6 + odio * 0.5 + (20 if controle_baixo else 0) - _num(psique, "t_empatia") * 0.3 + max(0, _num(psique, "dor") - 60) * 0.3,
        "frio": emocoes["nojo"] * 0.3 + emocoes["tristeza"] * 0.3 + max(0, 40 - energia) * 0.5 - amor * 0.3,
        "terno": amor * 0.6 + emocoes["confianca"] * 0.3 + _num(psique, "t_empatia") * 0.2 - emocoes["raiva"] * 0.4,
        "fervoroso": paixao * 0.7 + emocoes["expectativa"] * 0.3,
        "amargo": emocoes["tristeza"] * 0.4 + emocoes["raiva"] * 0.3 + odio * 0.3,
        "brincalhão": emocoes["alegria"] * 0.5 + emocoes["surpresa"] * 0.2 - emocoes["medo"] * 0.3,
    }
    ativos_tom = sorted(((k, v) for k, v in tons.items() if v >= 30), key=lambda x: -x[1])[:3]
    psique.set("tom", ", ".join(f"{k} ({v:.0f})" for k, v in ativos_tom) or "sereno")
    penalidade = (max(0, medo - 40) * 0.3 + max(0, 50 - energia) * 0.3 + max(0, _num(psique, "dor") - 50) * 0.3
                  + (15 if saude_ativos.get("tdah") else 0) + (15 if saude_ativos.get("depressao") else 0)
                  + (10 if saude_ativos.get("burnout") or saude_ativos.get("insonia") else 0))
    psique.set("penalidade_de_desempenho", str(_clamp(penalidade)))


def sortear_impulso(psique: Registro, nome_evento: str = "") -> bool:
    """Às vezes ele age por impulso: sorteio real contra o impulso atual."""
    return _RNG.random() * 100 < _num(psique, "impulso") * 0.6


def _atualizar_saude(saude: Registro, cargas_delta: dict[str, float], hoje: date) -> list[str]:
    """Aplica cargas, decide onset, subclínico, remissão. Retorna mudanças de estado."""
    mudancas = []
    for transtorno in TRANSTORNOS:
        carga = _clamp(_num(saude, f"{transtorno}_carga") + cargas_delta.get(transtorno, 0))
        saude.set(f"{transtorno}_carga", str(carga))
        pre = _num(saude, f"{transtorno}_predisposicao")
        limiar = max(20, (100 - pre) * _ruido(0.12))  # o corpo não avisa sempre no mesmo ponto
        estado = saude.get(f"{transtorno}_estado")
        novo = estado
        if estado in ("latente", "remissao") and carga >= limiar:
            novo = "ativo"
        elif estado in ("latente", "remissao") and carga >= limiar / 2:
            novo = "subclinico"
        elif estado == "subclinico" and carga >= limiar:
            novo = "ativo"
        elif estado == "subclinico" and carga < limiar / 2:
            novo = "latente"
        elif estado == "ativo" and carga < limiar / 2:
            novo = "remissao"
        if novo != estado:
            saude.set(f"{transtorno}_estado", novo)
            saude.set(f"{transtorno}_mudou_em", hoje.isoformat())
            mudancas.append(f"{transtorno}: {estado} → {novo}")
    sintomas = []
    for transtorno in TRANSTORNOS:
        estado = saude.get(f"{transtorno}_estado")
        if estado == "ativo":
            rotulo = transtorno if saude.get(f"{transtorno}_diagnostico", "nao").startswith("sim") else "sem nome"
            sintomas.append(f"[{rotulo}] {TRANSTORNOS[transtorno]}")
        elif estado == "subclinico":
            sintomas.append(f"[leve, sem nome] {TRANSTORNOS[transtorno].split(',')[0]}, de vez em quando")
    saude.set("sintomas_ativos", "; ".join(sintomas) or "nenhum")
    return mudancas


def _pessoa(estado: dict, nome: str) -> Registro:
    for registro in estado["pessoas"]:
        if registro.get("nome", "").lower() == nome.lower():
            return registro
    novo = Registro(proximo_id("P", estado["pessoas"]), {"nome": nome, "confianca": "50", "afeto": "0", "paixao": "0",
                                                          "influencia": "25", "eventos": "0", "ultimo_evento": "nenhum"})
    estado["pessoas"].append(novo)
    return novo


def _gravar(estado: dict, evento: str, intensidade: str, descricao: str, relatado_por: str, pessoa: str,
            deltas: dict[str, float], mudancas: list[str], hoje: date) -> Registro:
    psique = estado["psique"]
    psique.set("experiencias", str(int(_num(psique, "experiencias")) + 1))
    psique.set("plasticidade", str(_clamp(max(15, 90 - int(_num(psique, "experiencias")) * 0.4))))
    ativos = {t: True for t in _ativos(estado["saude"])}
    _derivar(psique, ativos)
    por_impulso = evento not in ("tempo", "significado", "pratica") and sortear_impulso(psique, evento)
    psique.set("agiu_por_impulso", "sim: respondeu antes de terminar a análise; corrige depois" if por_impulso
               else "nao")
    psique.set("atualizado_em", hoje.isoformat())
    psique.set("ultimo_evento", evento)
    for registro in estado["pessoas"]:
        influ = _num(registro, "confianca") * _num(psique, "influenciabilidade") / 100
        registro.set("influencia", str(_clamp(influ)))
    texto = "; ".join(f"{k} {v:+.0f}" for k, v in deltas.items() if abs(v) >= 0.5) or "nenhum"
    registro = Registro(proximo_id("PH", estado["historico"]), {
        "evento": evento, "intensidade": intensidade, "pessoa": pessoa or "-",
        "descricao": descricao or EVENTOS.get(evento, {}).get("descricao", ""), "relatado_por": relatado_por,
        "deltas": texto, "saude": "; ".join(mudancas) or "sem mudança",
        "emocao_dominante_apos": psique.get("emocao_dominante"), "ego_apos": psique.get("ego"),
        "postura_apos": psique.get("postura"), "impulso": "agiu por impulso" if por_impulso else "controlado",
        "data": hoje.isoformat(),
    })
    estado["historico"].append(registro)
    return registro


def aplicar_evento(estado: dict, evento: str, intensidade: str = "normal", descricao: str = "",
                   pessoa: str = "", relatado_por: str = "NEX", hoje: date | None = None) -> Registro:
    hoje = hoje or date.today()
    if evento not in EVENTOS:
        raise ErroDePsique(f"evento desconhecido '{evento}'. Use: {', '.join(sorted(EVENTOS))}")
    if intensidade not in INTENSIDADES:
        raise ErroDePsique("intensidade deve ser leve, normal ou forte")
    fator = INTENSIDADES[intensidade]
    dados = EVENTOS[evento]
    psique, saude = estado["psique"], estado["saude"]
    deltas: dict[str, float] = {}
    impulsividade = _num(psique, "t_impulsividade") / 100
    for emocao, delta in dados.get("e", {}).items():
        d = delta * fator * (0.7 + 0.6 * impulsividade) * _ruido()
        psique.set(f"e_{emocao}", str(_clamp(_num(psique, f"e_{emocao}") + d)))
        deltas[emocao] = d
    if _RNG.random() < 0.25:  # ricochete: uma emoção que ninguém previu
        extra = _RNG.choice(EMOCOES)
        d = _RNG.uniform(-8, 12) * fator
        psique.set(f"e_{extra}", str(_clamp(_num(psique, f"e_{extra}") + d)))
        deltas[f"{extra} (ricochete)"] = d
    if "ego" in dados:
        orgulho = _num(psique, "t_orgulho") / 100
        d = dados["ego"] * fator * (0.6 + 0.8 * orgulho) if dados["ego"] > 0 else dados["ego"] * fator * (1.4 - 0.8 * orgulho)
        d *= _ruido()
        psique.set("ego", str(_clamp(_num(psique, "ego") + d)))
        deltas["ego"] = d
    if "energia" in dados:
        d = dados["energia"] * fator * _ruido(0.3)
        psique.set("energia", str(_clamp(_num(psique, "energia") + d)))
        deltas["energia"] = d
    if "dor" in dados:
        d = dados["dor"] * fator * _ruido(0.3)
        psique.set("dor", str(_clamp(_num(psique, "dor") + d)))
        deltas["dor"] = d
    cargas = {}
    resiliencia = _num(psique, "t_resiliencia") / 100
    for transtorno, delta in dados.get("c", {}).items():
        if transtorno not in TRANSTORNOS:
            continue
        pre = _num(saude, f"{transtorno}_predisposicao") / 100
        if delta > 0:
            d = delta * fator * (0.5 + pre) * (1.3 - 0.6 * resiliencia) * _ruido()
        else:
            d = delta * fator * _ruido(0.3)
        cargas[transtorno] = d
        deltas[f"carga_{transtorno}"] = d
    if evento == "avaliacao":
        for transtorno in _ativos(saude):
            saude.set(f"{transtorno}_diagnostico", f"sim, em {hoje.isoformat()}")
    mudancas = _atualizar_saude(saude, cargas, hoje)
    empatia = _num(psique, "t_empatia") / 100
    for complexa in COMPLEXAS:
        if complexa in dados:
            d = dados[complexa] * fator * (0.6 + 0.8 * empatia if dados[complexa] > 0 else 1.0) * _ruido()
            psique.set(complexa, str(_clamp(_num(psique, complexa) + d)))
            deltas[complexa] = d
    if pessoa:
        registro_pessoa = _pessoa(estado, pessoa)
        d = dados.get("pessoa", 0) * fator * _ruido()
        registro_pessoa.set("confianca", str(_clamp(_num(registro_pessoa, "confianca") + d)))
        if "afeto" in dados:
            da = dados["afeto"] * fator * _ruido()
            afeto = max(-100.0, min(100.0, _num(registro_pessoa, "afeto") + da))
            registro_pessoa.set("afeto", str(int(round(afeto))))
            deltas[f"afeto_por_{pessoa}"] = da
        if "paixao" in dados and dados["paixao"] > 0:
            registro_pessoa.set("paixao", str(_clamp(_num(registro_pessoa, "paixao") + dados["paixao"] * fator)))
        registro_pessoa.set("eventos", str(int(_num(registro_pessoa, "eventos")) + 1))
        registro_pessoa.set("ultimo_evento", f"{evento} em {hoje.isoformat()}")
        deltas[f"confianca_em_{pessoa}"] = d
    if "valor" in dados:
        valor, delta = dados["valor"]
        d = delta * fator * _num(psique, "plasticidade") / 100 * _ruido()
        psique.set(f"v_{valor}", str(_clamp(_num(psique, f"v_{valor}") + d)))
        deltas[f"v_{valor}"] = d
    return _gravar(estado, evento, intensidade, descricao, relatado_por, pessoa, deltas, mudancas, hoje)


def aplicar_significado(estado: dict, fonte: str, conteudo: str, significado: str, emocao: str,
                        intensidade: str, valor: str, direcao: str, relatado_por: str = "NEX",
                        hoje: date | None = None) -> Registro:
    """Ler um fato ou um livro e compreender o que significa: é isso que forma o caráter."""
    hoje = hoje or date.today()
    if emocao not in EMOCOES:
        raise ErroDePsique(f"emocao deve ser uma de: {', '.join(EMOCOES)}")
    if valor not in VALORES:
        raise ErroDePsique(f"valor deve ser um de: {', '.join(VALORES)}")
    if intensidade not in INTENSIDADES:
        raise ErroDePsique("intensidade deve ser leve, normal ou forte")
    if direcao not in ("+", "-"):
        raise ErroDePsique("direcao deve ser '+' ou '-'")
    psique = estado["psique"]
    fator = INTENSIDADES[intensidade]
    plasticidade = _num(psique, "plasticidade") / 100
    abertura = _num(psique, "t_abertura") / 100
    d_valor = (6 if direcao == "+" else -6) * fator * plasticidade * (0.6 + 0.8 * abertura) * _ruido()
    psique.set(f"v_{valor}", str(_clamp(_num(psique, f"v_{valor}") + d_valor)))
    d_emocao = 10 * fator * _ruido()
    psique.set(f"e_{emocao}", str(_clamp(_num(psique, f"e_{emocao}") + d_emocao)))
    deltas = {f"v_{valor}": d_valor, emocao: d_emocao}
    descricao = f"{fonte}: {conteudo} → significado: {significado}"
    return _gravar(estado, "significado", intensidade, descricao, relatado_por, "", deltas, [], hoje)


def aplicar_pratica(estado: dict, habilidade: str, resultado: str, dificuldade: str = "media",
                    descricao: str = "", relatado_por: str = "NEX", hoje: date | None = None) -> Registro:
    """Usar uma habilidade muda o nível dela: retornos decrescentes, fracasso ensina menos e custa ego."""
    hoje = hoje or date.today()
    hab = estado["habilidades"]
    if habilidade not in habilidades_de(estado):
        raise ErroDePsique(f"habilidade desconhecida '{habilidade}'. Use: {', '.join(sorted(habilidades_de(estado)))}")
    if resultado not in RESULTADOS:
        raise ErroDePsique("resultado deve ser sucesso, parcial ou fracasso")
    if dificuldade not in DIFICULDADES:
        raise ErroDePsique("dificuldade deve ser facil, media ou dificil")
    psique = estado["psique"]
    nivel = _num(hab, habilidade)
    ganho = 4.0 * DIFICULDADES[dificuldade] * RESULTADOS[resultado] * ((100 - nivel) / 100) ** 1.5 * (0.5 + _num(psique, "t_curiosidade") / 200) * _ruido(0.5)
    if dificuldade == "facil" and nivel >= 80:
        ganho = 0.0
    hab.set(habilidade, str(round(min(100.0, nivel + ganho), 2)))
    hab.set(f"{habilidade}_ultima_pratica", hoje.isoformat())  # registro; habilidade nunca se perde por desuso
    deltas = {habilidade: ganho}
    if resultado == "sucesso":
        d = 2 * DIFICULDADES[dificuldade]
        psique.set("ego", str(_clamp(_num(psique, "ego") + d)))
        psique.set("e_alegria", str(_clamp(_num(psique, "e_alegria") + 4)))
        deltas["ego"] = d
    elif resultado == "fracasso":
        d = -3 * DIFICULDADES[dificuldade]
        psique.set("ego", str(_clamp(_num(psique, "ego") + d)))
        psique.set("e_tristeza", str(_clamp(_num(psique, "e_tristeza") + 4)))
        deltas["ego"] = d
    texto = f"{habilidade} ({dificuldade}, {resultado}): {nivel:.1f} → {_num(hab, habilidade):.1f} [{nivel_de(_num(hab, habilidade))}]"
    return _gravar(estado, "pratica", "normal", (descricao + " " if descricao else "") + texto, relatado_por, "", deltas, [], hoje)


def passar_tempo(estado: dict, dias: int, relatado_por: str = "Milan", hoje: date | None = None) -> Registro:
    hoje = hoje or date.today()
    if dias <= 0:
        raise ErroDePsique("dias deve ser maior que zero")
    psique, saude = estado["psique"], estado["saude"]
    ativos = {t: True for t in _ativos(saude)}
    inicio = {e: _num(psique, f"e_{e}") for e in EMOCOES}
    cargas: dict[str, float] = {}
    oscilacoes = 0
    for _ in range(dias):
        for emocao in EMOCOES:
            atual = _num(psique, f"e_{emocao}")
            base = _base_emocional(psique, emocao, ativos)
            psique.set(f"e_{emocao}", str(max(0.0, min(100.0, atual + (base - atual) * _RNG.uniform(0.15, 0.35)))))
        if _RNG.random() < 0.2:  # oscilação de humor sem causa
            emocao = _RNG.choice(EMOCOES)
            psique.set(f"e_{emocao}", str(max(0.0, min(100.0, _num(psique, f"e_{emocao}") + _RNG.uniform(-12, 15)))))
            oscilacoes += 1
        dor = _num(psique, "dor")
        psique.set("dor", str(max(0.0, min(100.0, dor + (_num(psique, "dor_base") - dor) * _RNG.uniform(0.2, 0.5)
                                              + _RNG.uniform(-4, 4)))))
        energia = _num(psique, "energia")
        alvo = 45 if ativos.get("depressao") or ativos.get("burnout") else 80
        alvo = _jitter(alvo - _num(psique, "dor") * 0.3, 8)  # dia bom, dia ruim; dor cansa
        psique.set("energia", str(max(0.0, min(100.0, energia + (alvo - energia) * _RNG.uniform(0.1, 0.3)))))
        for transtorno in TRANSTORNOS:
            cargas[transtorno] = cargas.get(transtorno, 0) - (1.5 if transtorno != "tdah" else 0.5) * _ruido(0.5)
        ego = _num(psique, "ego")
        psique.set("ego", str(max(0.0, min(100.0, ego + (50 - ego) * 0.05 + _RNG.uniform(-1.5, 1.5)))))
        for complexa in COMPLEXAS:  # amor, ódio e paixão são lentos e caprichosos
            psique.set(complexa, str(max(0.0, _num(psique, complexa) * _RNG.uniform(0.96, 0.995))))
    for complexa in COMPLEXAS:
        psique.set(complexa, str(_clamp(_num(psique, complexa))))
    for emocao in EMOCOES:
        psique.set(f"e_{emocao}", str(_clamp(_num(psique, f"e_{emocao}"))))
    psique.set("energia", str(_clamp(_num(psique, "energia"))))
    psique.set("ego", str(_clamp(_num(psique, "ego"))))
    psique.set("dor", str(_clamp(_num(psique, "dor"))))
    mudancas = _atualizar_saude(saude, cargas, hoje)
    deltas = {e: _num(psique, f"e_{e}") - inicio[e] for e in EMOCOES}
    return _gravar(estado, "tempo", "normal", f"{dias} dia(s) se passaram"
                   + (f"; {oscilacoes} oscilação(ões) de humor sem causa" if oscilacoes else ""),
                   relatado_por, "", deltas, mudancas, hoje)


# ---------------------------------------------------------------------- acaso
def sortear_acaso(estado: dict, rng: random.Random | None = None, quantos: int = 1) -> list[tuple[str, str, str]]:
    """Eventos de vida sorteados, ponderados pelo estado: devolve (evento, intensidade, pessoa)."""
    rng = rng or _RNG
    psique, saude = estado["psique"], estado["saude"]
    energia = _num(psique, "energia")
    pessoas = [p.get("nome") for p in estado["pessoas"]]
    pesos: dict[str, float] = {}
    for nome, dados in EVENTOS.items():
        if nome in ("avaliacao", "medicacao", "terapia"):
            continue  # só Milan decide tratamento e avaliação
        peso = 1.0
        if nome in RECUPERACAO:
            peso *= 1.4 if energia < 40 else 0.8
        if nome in ("sobrecarga", "sono_ruim", "prazo_perdido") and energia < 30:
            peso *= 1.5
        if nome in ("isolamento",) and not pessoas:
            peso *= 1.5
        if nome in ("gentileza_recebida", "cumplicidade", "brincadeira", "convivio") and pessoas:
            peso *= 1.3
        if nome in ("encantamento", "fascinio"):
            peso *= 0.5 + _num(psique, "t_curiosidade") / 100
        if nome in ("perda_de_alguem", "traicao", "humilhacao", "medo_intenso"):
            peso *= 0.25  # raros
        if nome in ("dor_forte", "analgesico", "abstinencia", "fisioterapia"):
            peso *= 1.6 if _num(psique, "dor_base") > 0 else 0.0
        pesos[nome] = peso
    escolhidos = []
    nomes = list(pesos)
    for _ in range(quantos):
        evento = rng.choices(nomes, weights=[pesos[n] for n in nomes])[0]
        intensidade = rng.choices(list(INTENSIDADES), weights=[3, 5, 2])[0]
        precisa_pessoa = "pessoa" in EVENTOS[evento] or "afeto" in EVENTOS[evento]
        pessoa = ""
        if precisa_pessoa:
            pessoa = rng.choice(pessoas) if pessoas and rng.random() < 0.75 else rng.choice(
                ["um desconhecido", "um colega", "um cliente", "alguém da família"])
        escolhidos.append((evento, intensidade, pessoa))
    return escolhidos


# -------------------------------------------------------------------- leitura
def resumo(estado: dict, ultimos: int = 8) -> str:
    psique, saude = estado["psique"], estado["saude"]
    linhas = [f"Emoção dominante: **{psique.get('emocao_dominante')}** · postura: **{psique.get('postura')}** · "
              f"ego {psique.get('ego')} ({psique.get('ego_leitura')}) · energia {psique.get('energia')} · "
              f"plasticidade {psique.get('plasticidade')} · influenciabilidade {psique.get('influenciabilidade')}.",
              "", f"**Mistura do momento:** {psique.get('mistura')}.", f"**Tom:** {psique.get('tom')}.",
              f"Amor {psique.get('amor')} · ódio {psique.get('odio')} · paixão {psique.get('paixao')}"
              + (f" · dor {psique.get('dor')} (base {psique.get('dor_base')})" if _num(psique, "dor_base") or _num(psique, "dor") else "") + ".",
              "", f"Caráter (valores mais fortes): {psique.get('carater')}.", "",
              "| Emoção | Valor |", "|---|---|"]
    linhas += [f"| {e} | {psique.get('e_' + e)} |" for e in EMOCOES]
    linhas += ["", "| Traço | Valor |", "|---|---|"]
    linhas += [f"| {t} | {psique.get('t_' + t)} |" for t in TRACOS]
    linhas += ["", "| Valor | Força |", "|---|---|"]
    linhas += [f"| {v} | {psique.get('v_' + v)} |" for v in VALORES]
    linhas += ["", f"Impulso {psique.get('impulso')}: último evento {'**agiu por impulso**' if psique.get('agiu_por_impulso', 'nao').startswith('sim') else 'controlado'}. "
               f"Penalidade de desempenho hoje: {psique.get('penalidade_de_desempenho')} pontos (medo, cansaço, atenção).", ""]
    habilidades = habilidades_de(estado)
    if habilidades:
        penal = _num(psique, "penalidade_de_desempenho")
        linhas += ["| Habilidade | Nível | Hoje (com penalidade) |", "|---|---|---|"]
        for nome_h, nivel in sorted(habilidades.items(), key=lambda x: -x[1]):
            hoje_n = max(0.0, nivel - penal)
            linhas.append(f"| {nome_h} | {nivel:.0f} ({nivel_de(nivel)}) | {hoje_n:.0f} ({nivel_de(hoje_n)}) |")
        linhas.append("")
    linhas += ["", f"**O que ele sente (sem necessariamente saber o nome):** {saude.get('sintomas_ativos')}", ""]
    diagnosticados = [t for t in TRANSTORNOS if saude.get(f"{t}_diagnostico", "nao").startswith("sim")]
    linhas.append("Diagnósticos conhecidos: " + (", ".join(diagnosticados) if diagnosticados else "nenhum (nada avaliado ainda)."))
    if estado["pessoas"]:
        linhas += ["", "| Pessoa | Confiança | Afeto (-100 ódio … +100 amor) | Paixão | Influência sobre ele |", "|---|---|---|---|---|"]
        linhas += [f"| {p.get('nome')} | {p.get('confianca')} | {p.get('afeto', '0')} | {p.get('paixao', '0')} | {p.get('influencia')} |"
                   for p in estado["pessoas"]]
    if estado["historico"]:
        linhas += ["", "Últimos eventos:"]
        for r in estado["historico"][-ultimos:]:
            linhas.append(f"- {r.id} {r.get('data')}: {r.get('evento')} ({r.get('intensidade')}"
                          + (f", {r.get('pessoa')}" if r.get('pessoa') not in ("-", "") else "")
                          + f") → {r.get('emocao_dominante_apos')}, ego {r.get('ego_apos')}, {r.get('postura_apos')}. {r.get('descricao')}")
    return "\n".join(linhas) + "\n"


def linha_de_estado(estado: dict) -> str:
    psique, saude = estado["psique"], estado["saude"]
    ativos = _ativos(saude)
    extra = f"; ativo sem nome: {len(ativos)} quadro(s)" if ativos else ""
    return (f"emoção {psique.get('emocao_dominante')}, tom {psique.get('tom')}, postura {psique.get('postura')}, "
            f"ego {psique.get('ego')}, energia {psique.get('energia')}{extra}")


def alertas(estado: dict) -> list[str]:
    """Evidências para ATLAS: quadros ativos, energia crítica, ego extremo."""
    psique, saude = estado["psique"], estado["saude"]
    saida = []
    for transtorno in _ativos(saude):
        saida.append(f"quadro ativo ({transtorno}, {'diagnosticado' if saude.get(f'{transtorno}_diagnostico', 'nao').startswith('sim') else 'sem diagnóstico'})")
    if _num(psique, "energia") <= 20:
        saida.append("energia crítica")
    if _num(psique, "ego") >= 85:
        saida.append("ego inflado: risco de defender erro")
    if _num(psique, "ego") <= 15:
        saida.append("ego ferido: risco de ceder a pressão")
    if _num(psique, "impulso") >= 70:
        saida.append("impulso alto: pode responder antes de terminar a análise")
    if _num(psique, "odio") >= 60:
        saida.append("ódio alto: tom hostil provável")
    if _num(psique, "dor") >= 75:
        saida.append("dor acima do suportável: julgamento e paciência reduzidos")
    return saida
