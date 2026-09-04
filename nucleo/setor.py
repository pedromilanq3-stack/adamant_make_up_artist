"""Um setor: cinco camadas em arquivos markdown dentro de uma pasta própria.

    camada1_nucleo.md      travada — missão, limites, método, agentes (hash conferido)
    camada2_fatos.md       F-nnn  fatos verificados
    camada3_hipoteses.md   H-nnn  hipóteses com teste, revisão e condição de abandono
    camada4_licoes.md      L-nnn  lições e resultados (histórico preservado)
    camada5_estado.md      ESTADO tarefa ativa, prazo, próxima ação, bloqueios, autorizações

O setor nunca apaga um registro: uma correção acrescenta um registro novo e marca o
anterior como superado, apontando para o substituto.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .registros import Registro, parse_registros, proximo_id, render_registros

CAMADAS = {
    1: "camada1_nucleo.md",
    2: "camada2_fatos.md",
    3: "camada3_hipoteses.md",
    4: "camada4_licoes.md",
    5: "camada5_estado.md",
}
PREFIXOS = {"fato": "F", "hipotese": "H", "licao": "L"}
CAMADA_DO_TIPO = {"fato": 2, "hipotese": 3, "licao": 4}

CAMPOS_OBRIGATORIOS = {
    "fato": ("conteudo", "fonte", "data", "confianca", "setor_origem", "volatil", "status"),
    "hipotese": (
        "conteudo", "evidencia_favoravel", "evidencia_contraria", "teste", "revisao",
        "abandono", "status",
    ),
    "licao": ("conteudo", "origem", "data", "status"),
    "estado": ("tarefa_ativa", "prazo", "proxima_acao", "bloqueios", "autorizacoes_pendentes",
               "atualizado_em"),
}
VALORES_PERMITIDOS = {
    "confianca": {"alta", "media", "baixa"},
    "volatil": {"sim", "nao"},
    "origem": {"resultado", "experimento", "correcao_milan", "evidencia"},
}
STATUS_PERMITIDOS = {
    "fato": {"vigente", "superado"},
    "hipotese": {"aberta", "confirmada", "refutada", "abandonada", "superada"},
    "licao": {"vigente", "superada"},
}
STATUS_SUPERADO = {"fato": "superado", "hipotese": "superada", "licao": "superada"}
DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_SETOR = re.compile(r"^S\d{2}$")

SECOES_DA_CAMADA_1 = (
    "Missão", "Responsabilidade", "Limites", "Método de análise", "Ferramentas permitidas",
    "Formato de saída", "Métricas", "Condições de parada", "Agentes",
)


class ErroDeValidacao(ValueError):
    pass


def hash_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _data_valida(valor: str) -> bool:
    if not DATA.match(valor):
        return False
    try:
        date.fromisoformat(valor)
    except ValueError:
        return False
    return True


@dataclass
class Setor:
    id: str
    pasta: Path
    preambulos: dict[int, str] = field(default_factory=dict)
    registros: dict[int, list[Registro]] = field(default_factory=dict)

    # ---------------------------------------------------------------- leitura
    @classmethod
    def carregar(cls, id_setor: str, pasta: Path) -> "Setor":
        setor = cls(id_setor, Path(pasta))
        for numero, nome in CAMADAS.items():
            caminho = setor.pasta / nome
            if not caminho.exists():
                raise ErroDeValidacao(f"{id_setor}: falta {nome}")
            texto = caminho.read_text(encoding="utf-8")
            if numero == 1:
                setor.preambulos[1] = texto
                setor.registros[1] = []
                continue
            preambulo, registros = parse_registros(texto)
            setor.preambulos[numero] = preambulo
            setor.registros[numero] = registros
        return setor

    @property
    def nome(self) -> str:
        for linha in self.camada1.splitlines():
            if linha.startswith("# "):
                return linha[2:].strip()
        return self.id

    @property
    def camada1(self) -> str:
        return self.preambulos[1]

    def hash_camada1(self) -> str:
        return hash_texto(self.camada1)

    @property
    def fatos(self) -> list[Registro]:
        return self.registros[2]

    @property
    def hipoteses(self) -> list[Registro]:
        return self.registros[3]

    @property
    def licoes(self) -> list[Registro]:
        return self.registros[4]

    @property
    def estado(self) -> Registro:
        for registro in self.registros[5]:
            if registro.id == "ESTADO":
                return registro
        raise ErroDeValidacao(f"{self.id}: camada5_estado.md precisa do registro '## ESTADO'")

    def buscar(self, id_registro: str) -> tuple[int, Registro] | None:
        for numero in (2, 3, 4):
            for registro in self.registros[numero]:
                if registro.id == id_registro:
                    return numero, registro
        return None

    # -------------------------------------------------------------- validação
    def validar(self) -> list[str]:
        problemas: list[str] = []
        for secao in SECOES_DA_CAMADA_1:
            if not re.search(rf"^##\s+{re.escape(secao)}\b", self.camada1, re.MULTILINE):
                problemas.append(f"{self.id}/camada1: falta a seção '## {secao}'")
        for tipo, numero in CAMADA_DO_TIPO.items():
            prefixo = PREFIXOS[tipo]
            vistos: set[str] = set()
            for registro in self.registros[numero]:
                if registro.id in vistos:
                    problemas.append(f"{self.id}/{CAMADAS[numero]}: id repetido {registro.id}")
                vistos.add(registro.id)
                if not re.match(rf"^{prefixo}-\d{{3,}}$", registro.id):
                    problemas.append(
                        f"{self.id}/{CAMADAS[numero]}: id {registro.id} deveria ser {prefixo}-nnn"
                    )
                problemas.extend(self._validar_registro(tipo, registro, CAMADAS[numero]))
        try:
            estado = self.estado
        except ErroDeValidacao as erro:
            problemas.append(str(erro))
        else:
            problemas.extend(self._validar_registro("estado", estado, CAMADAS[5]))
        return problemas

    def _validar_registro(self, tipo: str, registro: Registro, arquivo: str) -> list[str]:
        onde = f"{self.id}/{arquivo}/{registro.id}"
        problemas = [
            f"{onde}: falta o campo '{campo}'"
            for campo in CAMPOS_OBRIGATORIOS[tipo]
            if not registro.get(campo)
        ]
        for campo, permitidos in VALORES_PERMITIDOS.items():
            valor = registro.get(campo)
            if valor and campo in CAMPOS_OBRIGATORIOS[tipo] and valor not in permitidos:
                problemas.append(f"{onde}: {campo}='{valor}' não está em {sorted(permitidos)}")
        status = registro.get("status")
        if tipo in STATUS_PERMITIDOS and status and status not in STATUS_PERMITIDOS[tipo]:
            problemas.append(f"{onde}: status='{status}' não está em {sorted(STATUS_PERMITIDOS[tipo])}")
        for campo in ("data", "revisao", "reverificar_em", "atualizado_em", "superado_em"):
            valor = registro.get(campo)
            if valor and not _data_valida(valor):
                problemas.append(f"{onde}: {campo}='{valor}' não é uma data AAAA-MM-DD")
        if tipo == "fato":
            origem = registro.get("setor_origem")
            if origem and not ID_SETOR.match(origem):
                problemas.append(f"{onde}: setor_origem='{origem}' deveria ser Snn")
            if origem and origem != self.id and not registro.get("dossie"):
                problemas.append(
                    f"{onde}: fato vindo de {origem} precisa citar o dossiê que o trouxe (campo 'dossie')"
                )
            if registro.get("volatil") == "sim" and not registro.get("reverificar_em"):
                problemas.append(f"{onde}: fato volátil precisa de 'reverificar_em'")
        if status == STATUS_SUPERADO.get(tipo):
            substituto = registro.get("superado_por")
            if substituto and self.buscar(substituto) is None:
                problemas.append(f"{onde}: superado_por aponta para {substituto}, que não existe")
        return problemas

    # ---------------------------------------------------------------- escrita
    def acrescentar(self, tipo: str, campos: dict[str, str]) -> Registro:
        numero = CAMADA_DO_TIPO[tipo]
        registro = Registro(proximo_id(PREFIXOS[tipo], self.registros[numero]), dict(campos))
        self.registros[numero].append(registro)
        return registro

    def superar(self, id_antigo: str, motivo: str, hoje: str, substituto: str | None = None) -> Registro:
        encontrado = self.buscar(id_antigo)
        if encontrado is None:
            raise ErroDeValidacao(f"{self.id}: registro {id_antigo} não existe")
        numero, registro = encontrado
        tipo = {2: "fato", 3: "hipotese", 4: "licao"}[numero]
        if registro.get("status") == STATUS_SUPERADO[tipo]:
            raise ErroDeValidacao(f"{self.id}: {id_antigo} já estava superado")
        registro.set("status", STATUS_SUPERADO[tipo])
        registro.set("superado_em", hoje)
        registro.set("motivo_superacao", motivo)
        if substituto:
            registro.set("superado_por", substituto)
        return registro

    def definir_estado(self, campos: dict[str, str]) -> Registro:
        novo = Registro("ESTADO", dict(campos))
        self.registros[5] = [novo]
        return novo

    def salvar(self) -> None:
        self.pasta.mkdir(parents=True, exist_ok=True)
        (self.pasta / CAMADAS[1]).write_text(self.camada1, encoding="utf-8")
        for numero in (2, 3, 4, 5):
            texto = render_registros(self.preambulos[numero], self.registros[numero])
            (self.pasta / CAMADAS[numero]).write_text(texto, encoding="utf-8")

    # ------------------------------------------------------------ pendências
    def pendencias(self, hoje: date) -> list[str]:
        itens: list[str] = []
        for fato in self.fatos:
            if fato.get("status") != "vigente" or fato.get("volatil") != "sim":
                continue
            prazo = fato.get("reverificar_em")
            if prazo and _data_valida(prazo) and date.fromisoformat(prazo) <= hoje:
                itens.append(f"{fato.id}: reverificar fato volátil ({prazo}) — {fato.get('conteudo')}")
        for hipotese in self.hipoteses:
            if hipotese.get("status") != "aberta":
                continue
            prazo = hipotese.get("revisao")
            if prazo and _data_valida(prazo) and date.fromisoformat(prazo) <= hoje:
                itens.append(f"{hipotese.id}: revisar hipótese ({prazo}) — {hipotese.get('conteudo')}")
        try:
            estado = self.estado
        except ErroDeValidacao:
            return itens
        prazo = estado.get("prazo")
        if _data_valida(prazo) and date.fromisoformat(prazo) < hoje:
            itens.append(f"ESTADO: prazo da tarefa ativa venceu em {prazo} — {estado.get('tarefa_ativa')}")
        autorizacoes = estado.get("autorizacoes_pendentes", "").strip().lower()
        if autorizacoes and autorizacoes not in {"nenhuma", "nenhum", "-", "não há", "nao ha"}:
            itens.append(f"ESTADO: autorização pendente de Milan — {estado.get('autorizacoes_pendentes')}")
        return itens

    # ------------------------------------------------------------- métricas
    def metricas(self) -> dict[str, object]:
        fatos_vigentes = sum(1 for f in self.fatos if f.get("status") == "vigente")
        fatos_superados = len(self.fatos) - fatos_vigentes
        por_status: dict[str, int] = {}
        for hipotese in self.hipoteses:
            por_status[hipotese.get("status")] = por_status.get(hipotese.get("status"), 0) + 1
        calibracao: dict[str, dict[str, int]] = {}
        for hipotese in self.hipoteses:
            status = hipotese.get("status")
            if status not in {"confirmada", "refutada"}:
                continue
            faixa = hipotese.get("confianca") or "sem_confianca"
            faixa_dados = calibracao.setdefault(faixa, {"confirmadas": 0, "refutadas": 0})
            faixa_dados["confirmadas" if status == "confirmada" else "refutadas"] += 1
        licoes_por_origem: dict[str, int] = {}
        for licao in self.licoes:
            if licao.get("status") != "vigente":
                continue
            licoes_por_origem[licao.get("origem")] = licoes_por_origem.get(licao.get("origem"), 0) + 1
        return {
            "fatos_vigentes": fatos_vigentes,
            "fatos_superados": fatos_superados,
            "hipoteses": por_status,
            "calibracao": calibracao,
            "licoes_vigentes": licoes_por_origem,
            "licoes_superadas": sum(1 for l in self.licoes if l.get("status") == "superada"),
        }
