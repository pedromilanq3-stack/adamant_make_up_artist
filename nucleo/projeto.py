"""O Projeto: manifesto, setores, dossiês entre setores e o pacote enviado ao GPT.

Regras que este módulo faz cumprir por construção:

- um bloco de aprendizado só escreve no setor que o emitiu (ErroDeIsolamento);
- a Camada 1 de cada setor é travada por hash e só muda com autorização de Milan;
- nada é apagado: correções acrescentam e marcam o anterior como superado;
- conhecimento cruza setores apenas por dossiê mínimo; dossiê sensível ou amplo
  espera autorização de Milan antes de poder ser usado;
- setores nascem Propostos e só operam depois de Aprovado → Piloto → Ativo, cada
  passo autorizado por Milan.
"""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .patch import BlocoDeAprendizado, ErroDePatch, Secao
from .registros import Registro, parse_registros, proximo_id, render_registros
from .setor import (
    CAMADAS, CAMPOS_OBRIGATORIOS, PREFIXOS, SECOES_DA_CAMADA_1, STATUS_SUPERADO, ErroDeValidacao,
    Setor,
)

ESTADOS_DE_SETOR = ("Proposto", "Aprovado", "Piloto", "Ativo", "Pausado", "Encerrado")
TRANSICOES = {
    "aprovar": ("Proposto", "Aprovado"),
    "piloto": ("Aprovado", "Piloto"),
    "ativar": ("Piloto", "Ativo"),
    "reativar": ("Pausado", "Ativo"),
    "pausar": ("Ativo", "Pausado"),
    "encerrar": (("Piloto", "Ativo", "Pausado"), "Encerrado"),
}
ESTADOS_OPERANTES = {"Piloto", "Ativo"}
SECOES_DA_CARTA = (
    "Nome", "Missão", "Decisões sob sua responsabilidade", "Fora do escopo",
    "Cérebro e método de análise", "Agentes necessários", "Ferramentas permitidas",
    "Entradas e entregáveis", "Métricas", "Riscos", "Custo estimado",
    "Relações com outros setores", "Condição de suspensão ou encerramento",
)
CAMPOS_DO_DOSSIE = ("para", "fato", "fonte", "confianca", "restricao", "pergunta")
ARQUIVO_MANIFESTO = "manifesto.json"
ARQUIVO_INSTRUCOES = "INSTRUCOES_DO_PROJETO.md"
ARQUIVO_PROTOCOLO = "PROTOCOLO_DO_CEREBRO.md"
LIMITE_INSTRUCOES = 8000


class ErroDeAutorizacao(PermissionError):
    """A ação exige autorização explícita de Milan."""


class ErroDeIsolamento(PermissionError):
    """Um setor tentou escrever fora da própria memória."""


def slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sem_acento.lower()).strip("_")


def exige_milan(autorizado: bool, acao: str) -> None:
    if not autorizado:
        raise ErroDeAutorizacao(
            f"'{acao}' só pode ser feito por Milan. Repita com --autorizado-por-milan."
        )


@dataclass
class Projeto:
    raiz: Path
    manifesto: dict

    # ---------------------------------------------------------------- abrir
    @classmethod
    def abrir(cls, raiz: Path) -> "Projeto":
        raiz = Path(raiz)
        caminho = raiz / ARQUIVO_MANIFESTO
        if not caminho.exists():
            raise FileNotFoundError(f"não encontrei {caminho}")
        manifesto = json.loads(caminho.read_text(encoding="utf-8"))
        manifesto.setdefault("setores", {})
        manifesto.setdefault("versao", 1)
        return cls(raiz, manifesto)

    def salvar_manifesto(self) -> None:
        texto = json.dumps(self.manifesto, ensure_ascii=False, indent=2) + "\n"
        (self.raiz / ARQUIVO_MANIFESTO).write_text(texto, encoding="utf-8")

    @property
    def pasta_setores(self) -> Path:
        return self.raiz / "setores"

    @property
    def pasta_dossies(self) -> Path:
        return self.raiz / "dossies"

    @property
    def pasta_upload(self) -> Path:
        return self.raiz / "upload"

    def entrada(self, id_setor: str) -> dict:
        try:
            return self.manifesto["setores"][id_setor]
        except KeyError:
            raise ErroDeValidacao(f"setor {id_setor} não existe no manifesto") from None

    def setor(self, id_setor: str) -> Setor:
        entrada = self.entrada(id_setor)
        return Setor.carregar(id_setor, self.pasta_setores / entrada["pasta"])

    def setores(self) -> list[str]:
        return sorted(self.manifesto["setores"])

    def setores_com_camadas(self) -> list[str]:
        return [s for s in self.setores() if self.entrada(s)["status"] != "Proposto"]

    # ------------------------------------------------------------- validar
    def validar(self) -> list[str]:
        problemas: list[str] = []
        instrucoes = self.raiz / ARQUIVO_INSTRUCOES
        if not instrucoes.exists():
            problemas.append(f"falta {ARQUIVO_INSTRUCOES}")
        elif len(instrucoes.read_text(encoding="utf-8")) > LIMITE_INSTRUCOES:
            problemas.append(
                f"{ARQUIVO_INSTRUCOES} passa de {LIMITE_INSTRUCOES} caracteres; "
                "o campo de instruções do Projeto pode cortar o texto"
            )
        if not (self.raiz / ARQUIVO_PROTOCOLO).exists():
            problemas.append(f"falta {ARQUIVO_PROTOCOLO}")
        for id_setor in self.setores():
            entrada = self.entrada(id_setor)
            if entrada.get("status") not in ESTADOS_DE_SETOR:
                problemas.append(f"{id_setor}: status '{entrada.get('status')}' desconhecido")
            pasta = self.pasta_setores / entrada.get("pasta", "")
            if not pasta.is_dir():
                problemas.append(f"{id_setor}: pasta {pasta} não existe")
                continue
            if entrada.get("status") == "Proposto":
                if not (pasta / "carta.md").exists():
                    problemas.append(f"{id_setor}: setor proposto sem carta.md")
                continue
            try:
                setor = Setor.carregar(id_setor, pasta)
            except (ErroDeValidacao, ValueError) as erro:
                problemas.append(str(erro))
                continue
            problemas.extend(setor.validar())
            trava = entrada.get("trava_camada1")
            if not trava:
                problemas.append(f"{id_setor}: camada 1 não está travada (use 'travar')")
            elif trava != setor.hash_camada1():
                problemas.append(
                    f"{id_setor}: camada 1 foi alterada sem autorização (hash difere da trava)"
                )
            for fato in setor.fatos:
                referencia = fato.get("dossie")
                if referencia:
                    problemas.extend(self._conferir_dossie(fato, referencia, id_setor))
        for dossie in self.dossies():
            problemas.extend(self._validar_dossie(dossie))
        return problemas

    def _conferir_dossie(self, fato: Registro, referencia: str, destino: str) -> list[str]:
        dossie = self.dossie(referencia)
        if dossie is None:
            return [f"{destino}/{fato.id}: dossiê {referencia} não existe"]
        if dossie.get("para") != destino or dossie.get("de") != fato.get("setor_origem"):
            return [f"{destino}/{fato.id}: dossiê {referencia} não liga {fato.get('setor_origem')} → {destino}"]
        if dossie.get("status") not in {"autorizado", "entregue"}:
            return [f"{destino}/{fato.id}: dossiê {referencia} ainda não foi autorizado por Milan"]
        return []

    def _validar_dossie(self, dossie: Registro) -> list[str]:
        problemas = [
            f"{dossie.id}: falta o campo '{campo}'"
            for campo in ("de",) + CAMPOS_DO_DOSSIE + ("sensivel", "status", "data")
            if not dossie.get(campo)
        ]
        if dossie.get("status") not in {"pendente", "autorizado", "entregue", "recusado"}:
            problemas.append(f"{dossie.id}: status '{dossie.get('status')}' inválido")
        for chave in ("de", "para"):
            valor = dossie.get(chave)
            if valor and valor not in self.manifesto["setores"]:
                problemas.append(f"{dossie.id}: {chave}={valor} não é um setor do projeto")
        return problemas

    # ------------------------------------------------------------- travar
    def travar(self, id_setor: str, autorizado_por_milan: bool) -> str:
        exige_milan(autorizado_por_milan, f"travar a camada 1 de {id_setor}")
        setor = self.setor(id_setor)
        problemas = [p for p in setor.validar() if "/camada1" in p]
        if problemas:
            raise ErroDeValidacao("; ".join(problemas))
        entrada = self.entrada(id_setor)
        entrada["trava_camada1"] = setor.hash_camada1()
        entrada["camada1_travada_em"] = date.today().isoformat()
        self.salvar_manifesto()
        return entrada["trava_camada1"]

    # ------------------------------------------------------------ aplicar
    def aplicar(self, bloco: BlocoDeAprendizado, autorizado_por_milan: bool = False,
                hoje: date | None = None) -> list[str]:
        """Aplica o bloco ao setor emissor. Retorna o relato do que mudou."""
        hoje = hoje or date.today()
        entrada = self.entrada(bloco.setor)
        if entrada["status"] not in ESTADOS_OPERANTES:
            raise ErroDeAutorizacao(
                f"{bloco.setor} está '{entrada['status']}' e não opera; só setores em "
                f"{sorted(ESTADOS_OPERANTES)} recebem aprendizado"
            )
        trava = entrada.get("trava_camada1")
        setor = self.setor(bloco.setor)
        if trava and trava != setor.hash_camada1():
            raise ErroDeValidacao(
                f"{bloco.setor}: camada 1 difere da trava; corrija antes de aplicar aprendizado"
            )
        relato: list[str] = []
        pendentes: list[Registro] = []
        for secao in bloco.secoes:
            relato.append(self._aplicar_secao(setor, bloco, secao, hoje, autorizado_por_milan, pendentes))
        problemas = setor.validar()
        if problemas:
            raise ErroDePatch("o bloco deixaria o setor inválido:\n  " + "\n  ".join(problemas))
        setor.salvar()
        for dossie in pendentes:
            self._gravar_dossie(dossie)
        return relato

    def _aplicar_secao(self, setor: Setor, bloco: BlocoDeAprendizado, secao: Secao, hoje: date,
                       autorizado: bool, dossies: list[Registro]) -> str:
        campos = dict(secao.campos)
        data_hoje = hoje.isoformat()
        if secao.tipo in ("fato", "hipotese", "licao"):
            self._preencher_padroes(secao.tipo, campos, bloco, data_hoje)
            self._exigir_isolamento(setor, secao.tipo, campos, autorizado)
            novo = setor.acrescentar(secao.tipo, campos)
            return f"{novo.id} acrescentado ({secao.tipo})"
        if secao.tipo == "correcao":
            antigo_id = campos.pop("substitui", "")
            motivo = campos.pop("motivo", "") or "correção"
            if not antigo_id:
                raise ErroDePatch("'## correcao' precisa do campo 'substitui: <id>'")
            encontrado = setor.buscar(antigo_id)
            if encontrado is None:
                raise ErroDeIsolamento(
                    f"{antigo_id} não pertence a {setor.id}; um setor só corrige a própria memória"
                )
            numero, antigo = encontrado
            tipo = {2: "fato", 3: "hipotese", 4: "licao"}[numero]
            for chave, valor in antigo.campos.items():
                if chave not in campos and chave not in {"status", "superado_por", "superado_em",
                                                          "motivo_superacao", "registrado_em"}:
                    campos.setdefault(chave, valor)
            self._preencher_padroes(tipo, campos, bloco, data_hoje)
            campos["status"] = {"fato": "vigente", "hipotese": "aberta", "licao": "vigente"}[tipo]
            campos["corrige"] = antigo_id
            self._exigir_isolamento(setor, tipo, campos, autorizado)
            novo = setor.acrescentar(tipo, campos)
            setor.superar(antigo_id, motivo, data_hoje, substituto=novo.id)
            return f"{novo.id} acrescentado; {antigo_id} marcado como superado (histórico preservado)"
        if secao.tipo == "supera":
            if setor.buscar(secao.alvo) is None:
                raise ErroDeIsolamento(f"{secao.alvo} não pertence a {setor.id}")
            setor.superar(secao.alvo, campos.get("motivo", "superado"), data_hoje)
            return f"{secao.alvo} marcado como superado"
        if secao.tipo == "resultado":
            encontrado = setor.buscar(secao.alvo)
            if encontrado is None or encontrado[0] != 3:
                raise ErroDeIsolamento(f"{secao.alvo} não é uma hipótese de {setor.id}")
            hipotese = encontrado[1]
            status = campos.get("status", "")
            if status not in {"confirmada", "refutada", "abandonada"}:
                raise ErroDePatch("'## resultado' precisa de status confirmada, refutada ou abandonada")
            if hipotese.get("status") != "aberta":
                raise ErroDePatch(f"{secao.alvo} não está aberta (status atual: {hipotese.get('status')})")
            hipotese.set("status", status)
            hipotese.set("resultado", campos.get("resultado", ""))
            hipotese.set("encerrada_em", data_hoje)
            return f"{secao.alvo} → {status}"
        if secao.tipo == "estado":
            campos.setdefault("atualizado_em", data_hoje)
            campos.setdefault("atualizado_por", bloco.emitido_por)
            setor.definir_estado(campos)
            return "ESTADO substituído (as lições permanecem)"
        if secao.tipo == "dossie":
            dossie = self._montar_dossie(setor, bloco, campos, data_hoje, autorizado)
            dossies.append(dossie)
            return f"dossiê {dossie.id} de {setor.id} para {dossie.get('para')} ({dossie.get('status')})"
        raise ErroDePatch(f"seção desconhecida: {secao.tipo}")

    @staticmethod
    def _preencher_padroes(tipo: str, campos: dict[str, str], bloco: BlocoDeAprendizado,
                           data_hoje: str) -> None:
        campos.setdefault("registrado_em", data_hoje)
        campos.setdefault("registrado_por", bloco.emitido_por)
        if tipo == "fato":
            campos.setdefault("data", bloco.data)
            campos.setdefault("setor_origem", bloco.setor)
            campos.setdefault("volatil", "nao")
            campos.setdefault("status", "vigente")
        elif tipo == "hipotese":
            campos.setdefault("status", "aberta")
        elif tipo == "licao":
            campos.setdefault("data", bloco.data)
            campos.setdefault("status", "vigente")
        faltando = [c for c in CAMPOS_OBRIGATORIOS[tipo] if not campos.get(c)]
        if faltando:
            raise ErroDePatch(f"'## {tipo}' sem os campos obrigatórios: {', '.join(faltando)}")

    def _exigir_isolamento(self, setor: Setor, tipo: str, campos: dict[str, str],
                           autorizado: bool) -> None:
        if tipo != "fato":
            return
        origem = campos.get("setor_origem", setor.id)
        if origem == setor.id:
            return
        referencia = campos.get("dossie")
        if not referencia:
            raise ErroDeIsolamento(
                f"fato com setor_origem={origem} dentro de {setor.id} precisa vir por dossiê "
                "(campo 'dossie: D-nnn')"
            )
        problemas = self._conferir_dossie(Registro("novo", campos), referencia, setor.id)
        if problemas:
            raise ErroDeIsolamento("; ".join(problemas))
        dossie = self.dossie(referencia)
        if dossie is not None and dossie.get("status") == "autorizado":
            dossie.set("status", "entregue")
            self._gravar_dossie(dossie)

    # ------------------------------------------------------------ dossiês
    def dossies(self) -> list[Registro]:
        caminho = self.pasta_dossies / "dossies.md"
        if not caminho.exists():
            return []
        return parse_registros(caminho.read_text(encoding="utf-8"))[1]

    def dossie(self, id_dossie: str) -> Registro | None:
        for registro in self.dossies():
            if registro.id == id_dossie:
                return registro
        return None

    def _montar_dossie(self, setor: Setor, bloco: BlocoDeAprendizado, campos: dict[str, str],
                       data_hoje: str, autorizado: bool) -> Registro:
        faltando = [c for c in CAMPOS_DO_DOSSIE if not campos.get(c)]
        if faltando:
            raise ErroDePatch(f"'## dossie' sem os campos: {', '.join(faltando)}")
        destino = campos["para"]
        if destino == setor.id:
            raise ErroDePatch("um dossiê liga dois setores diferentes")
        if destino not in self.manifesto["setores"]:
            raise ErroDeIsolamento(f"setor de destino {destino} não existe")
        campos.setdefault("sensivel", "nao")
        campos.setdefault("amplo", "nao")
        precisa_milan = campos["sensivel"] == "sim" or campos["amplo"] == "sim"
        registro = Registro(proximo_id("D", self.dossies()))
        registro.set("de", setor.id)
        for chave in ("para", "fato", "fonte", "confianca", "restricao", "pergunta", "sensivel", "amplo"):
            registro.set(chave, campos[chave])
        registro.set("emitido_por", bloco.emitido_por)
        registro.set("data", data_hoje)
        if precisa_milan and not autorizado:
            registro.set("status", "pendente")
        else:
            registro.set("status", "autorizado")
            if precisa_milan:
                registro.set("autorizado_por", "Milan")
        return registro

    def _gravar_dossie(self, dossie: Registro) -> None:
        self.pasta_dossies.mkdir(parents=True, exist_ok=True)
        caminho = self.pasta_dossies / "dossies.md"
        if caminho.exists():
            preambulo, registros = parse_registros(caminho.read_text(encoding="utf-8"))
        else:
            preambulo, registros = (
                "# Dossiês entre setores\n\nCada dossiê leva um único fato ou conclusão de um "
                "setor para outro. Dossiê sensível ou amplo fica 'pendente' até Milan autorizar.",
                [],
            )
        registros = [r for r in registros if r.id != dossie.id] + [dossie]
        registros.sort(key=lambda r: r.id)
        caminho.write_text(render_registros(preambulo, registros), encoding="utf-8")

    def decidir_dossie(self, id_dossie: str, decisao: str, autorizado_por_milan: bool) -> Registro:
        exige_milan(autorizado_por_milan, f"decidir o dossiê {id_dossie}")
        if decisao not in {"autorizar", "recusar"}:
            raise ValueError("decisão deve ser 'autorizar' ou 'recusar'")
        dossie = self.dossie(id_dossie)
        if dossie is None:
            raise ErroDeValidacao(f"dossiê {id_dossie} não existe")
        if dossie.get("status") != "pendente":
            raise ErroDeValidacao(f"{id_dossie} não está pendente (status: {dossie.get('status')})")
        dossie.set("status", "autorizado" if decisao == "autorizar" else "recusado")
        dossie.set("decidido_por", "Milan")
        dossie.set("decidido_em", date.today().isoformat())
        self._gravar_dossie(dossie)
        return dossie

    # ---------------------------------------------------- ciclo de vida
    def propor_setor(self, id_setor: str, carta: str) -> Path:
        if not re.match(r"^S\d{2}$", id_setor):
            raise ErroDeValidacao("o id do setor deve ser S seguido de dois dígitos, por exemplo S02")
        if id_setor in self.manifesto["setores"]:
            raise ErroDeValidacao(f"{id_setor} já existe")
        faltando = [
            s for s in SECOES_DA_CARTA
            if not re.search(rf"^##\s+{re.escape(s)}\b", carta, re.MULTILINE)
        ]
        if faltando:
            raise ErroDeValidacao("carta incompleta; faltam as seções: " + ", ".join(faltando))
        nome = _secao_da_carta(carta, "Nome").strip().splitlines()[0] if _secao_da_carta(carta, "Nome").strip() else id_setor
        pasta = f"{id_setor}_{slug(nome)}"
        destino = self.pasta_setores / pasta
        destino.mkdir(parents=True, exist_ok=False)
        (destino / "carta.md").write_text(carta.rstrip("\n") + "\n", encoding="utf-8")
        self.manifesto["setores"][id_setor] = {
            "nome": nome, "pasta": pasta, "status": "Proposto",
            "proposto_em": date.today().isoformat(),
        }
        self.salvar_manifesto()
        return destino

    def transicionar(self, id_setor: str, acao: str, autorizado_por_milan: bool) -> str:
        exige_milan(autorizado_por_milan, f"{acao} o setor {id_setor}")
        if acao not in TRANSICOES:
            raise ValueError(f"ação desconhecida '{acao}'; use {sorted(TRANSICOES)}")
        entrada = self.entrada(id_setor)
        origens, destino = TRANSICOES[acao]
        origens = (origens,) if isinstance(origens, str) else origens
        if entrada["status"] not in origens:
            raise ErroDeValidacao(
                f"{id_setor} está '{entrada['status']}'; '{acao}' exige {' ou '.join(origens)}"
            )
        if acao == "aprovar":
            self._criar_camadas_da_carta(id_setor, entrada)
        entrada["status"] = destino
        entrada.setdefault("historico", []).append(
            {"de": origens[0] if len(origens) == 1 else "*", "para": destino,
             "em": date.today().isoformat(), "por": "Milan"}
        )
        self.salvar_manifesto()
        if acao == "aprovar":
            self.travar(id_setor, True)
        return destino

    def _criar_camadas_da_carta(self, id_setor: str, entrada: dict) -> None:
        pasta = self.pasta_setores / entrada["pasta"]
        carta = (pasta / "carta.md").read_text(encoding="utf-8")
        nome = entrada["nome"]
        hoje = date.today().isoformat()
        mapa = {
            "Missão": "Missão",
            "Responsabilidade": "Decisões sob sua responsabilidade",
            "Limites": "Fora do escopo",
            "Método de análise": "Cérebro e método de análise",
            "Ferramentas permitidas": "Ferramentas permitidas",
            "Formato de saída": "Entradas e entregáveis",
            "Métricas": "Métricas",
            "Condições de parada": "Condição de suspensão ou encerramento",
            "Agentes": "Agentes necessários",
        }
        partes = [f"# {id_setor} — {nome}", "",
                  "Camada 1 — Núcleo travado. Somente Milan altera este arquivo; depois de alterar, "
                  "execute `nucleo travar` com autorização.", ""]
        for secao in SECOES_DA_CAMADA_1:
            partes.append(f"## {secao}")
            partes.append("")
            partes.append(_secao_da_carta(carta, mapa[secao]).strip() or "(a definir por Milan)")
            partes.append("")
        (pasta / CAMADAS[1]).write_text("\n".join(partes).rstrip("\n") + "\n", encoding="utf-8")
        (pasta / CAMADAS[2]).write_text(
            f"# {id_setor} — Camada 2 — Fatos verificados\n\nCada fato registra conteúdo, fonte, "
            "data, confiança e setor de origem. Fato volátil precisa de `reverificar_em`.\n",
            encoding="utf-8",
        )
        (pasta / CAMADAS[3]).write_text(
            f"# {id_setor} — Camada 3 — Hipóteses\n\nHipótese nunca é apresentada como fato.\n",
            encoding="utf-8",
        )
        (pasta / CAMADAS[4]).write_text(
            f"# {id_setor} — Camada 4 — Lições e resultados\n\nUma correção não apaga o registro "
            "anterior: ele é marcado como superado.\n",
            encoding="utf-8",
        )
        estado = Registro("ESTADO", {
            "tarefa_ativa": "Piloto do setor: primeira tarefa a definir com Milan",
            "prazo": "a definir", "proxima_acao": "Perguntar a Milan qual é o primeiro problema deste setor",
            "bloqueios": "nenhum", "autorizacoes_pendentes": "nenhuma", "atualizado_em": hoje,
        })
        (pasta / CAMADAS[5]).write_text(
            render_registros(f"# {id_setor} — Camada 5 — Estado atual\n\nSomente a tarefa em curso.", [estado]),
            encoding="utf-8",
        )

    # --------------------------------------------------------- pendências
    def pendencias(self, hoje: date | None = None) -> dict[str, list[str]]:
        hoje = hoje or date.today()
        resultado: dict[str, list[str]] = {}
        for id_setor in self.setores_com_camadas():
            if self.entrada(id_setor)["status"] not in ESTADOS_OPERANTES:
                continue
            itens = self.setor(id_setor).pendencias(hoje)
            if itens:
                resultado[id_setor] = itens
        dossies = [
            f"{d.id}: {d.get('de')} → {d.get('para')} aguarda decisão de Milan — {d.get('fato')}"
            for d in self.dossies() if d.get("status") == "pendente"
        ]
        if dossies:
            resultado["dossies"] = dossies
        return resultado

    def metricas(self) -> dict[str, dict[str, object]]:
        return {s: self.setor(s).metricas() for s in self.setores_com_camadas()}

    # ---------------------------------------------------------- empacotar
    def empacotar(self, hoje: date | None = None) -> list[Path]:
        hoje = hoje or date.today()
        problemas = self.validar()
        if problemas:
            raise ErroDeValidacao("corrija antes de empacotar:\n  " + "\n  ".join(problemas))
        destino = self.pasta_upload
        if destino.exists():
            shutil.rmtree(destino)
        destino.mkdir(parents=True)
        gerados: list[Path] = []
        for origem, nome in ((ARQUIVO_INSTRUCOES, "00_INSTRUCOES_DO_PROJETO.md"),
                             (ARQUIVO_PROTOCOLO, "01_PROTOCOLO_DO_CEREBRO.md")):
            gerados.append(destino / nome)
            shutil.copyfile(self.raiz / origem, destino / nome)
        gerados.append(destino / "02_MANIFESTO.md")
        (destino / "02_MANIFESTO.md").write_text(self._manifesto_md(hoje), encoding="utf-8")
        for id_setor in self.setores():
            entrada = self.entrada(id_setor)
            pasta = self.pasta_setores / entrada["pasta"]
            nome = f"{id_setor}_{slug(entrada['nome']).upper()}.md"
            if entrada["status"] == "Proposto":
                texto = (f"# {id_setor} — {entrada['nome']} (PROPOSTO, não opera)\n\n"
                         + (pasta / "carta.md").read_text(encoding="utf-8"))
            else:
                texto = self._setor_md(id_setor, entrada, pasta, hoje)
            (destino / nome).write_text(texto, encoding="utf-8")
            gerados.append(destino / nome)
        dossies = self.dossies()
        if dossies:
            gerados.append(destino / "90_DOSSIES.md")
            shutil.copyfile(self.pasta_dossies / "dossies.md", destino / "90_DOSSIES.md")
        return gerados

    def _manifesto_md(self, hoje: date) -> str:
        linhas = ["# Manifesto do Projeto", "", f"Gerado em {hoje.isoformat()} pelo Núcleo. "
                  "Se um arquivo de setor no Projeto tiver hash diferente do listado aqui, ele está "
                  "desatualizado: avise Milan antes de confiar nele.", "", "## Setores", "",
                  "| Setor | Nome | Status | Hash da camada 1 | Fatos | Hipóteses | Lições |",
                  "|---|---|---|---|---|---|---|"]
        for id_setor in self.setores():
            entrada = self.entrada(id_setor)
            if entrada["status"] == "Proposto":
                linhas.append(f"| {id_setor} | {entrada['nome']} | Proposto | — | — | — | — |")
                continue
            setor = self.setor(id_setor)
            m = setor.metricas()
            linhas.append(
                f"| {id_setor} | {entrada['nome']} | {entrada['status']} | "
                f"{setor.hash_camada1()[:12]} | {m['fatos_vigentes']} | "
                f"{sum(m['hipoteses'].values())} | {sum(m['licoes_vigentes'].values())} |"
            )
        linhas += ["", "## Pendências de revisão", ""]
        pendencias = self.pendencias(hoje)
        if not pendencias:
            linhas.append("Nenhuma pendência.")
        for chave, itens in pendencias.items():
            linhas.append(f"### {chave}")
            linhas.extend(f"- {item}" for item in itens)
            linhas.append("")
        linhas += ["", "## Regras de leitura", "",
                   "- Setor Proposto, Pausado ou Encerrado não opera nem recebe aprendizado.",
                   "- Cada setor lê somente o próprio arquivo. Outro setor entra apenas por dossiê "
                   "autorizado (veja 90_DOSSIES.md, se existir).",
                   "- A Camada 1 é travada: nunca proponha alterá-la dentro de um bloco de aprendizado."]
        return "\n".join(linhas) + "\n"

    def _setor_md(self, id_setor: str, entrada: dict, pasta: Path, hoje: date) -> str:
        setor = Setor.carregar(id_setor, pasta)
        titulos = {2: "Camada 2 — Fatos verificados", 3: "Camada 3 — Hipóteses",
                   4: "Camada 4 — Lições e resultados", 5: "Camada 5 — Estado atual"}
        partes = [f"<!-- {id_setor} · status: {entrada['status']} · hash camada 1: "
                  f"{setor.hash_camada1()[:12]} · gerado em {hoje.isoformat()} -->", "",
                  "# " + setor.nome, "", f"Status: **{entrada['status']}**. Este arquivo é o cérebro "
                  f"completo do setor. A Camada 1 é travada (hash {setor.hash_camada1()[:12]}).", "",
                  "---", "", "## Camada 1 — Núcleo travado", "",
                  _rebaixar_titulos(_sem_titulo(setor.camada1))]
        for numero in (2, 3, 4, 5):
            texto = render_registros(_sem_titulo(setor.preambulos[numero]), setor.registros[numero])
            partes += ["", "---", "", f"## {titulos[numero]}", "", _rebaixar_titulos(texto)]
        return "\n".join(partes).rstrip("\n") + "\n"


def _secao_da_carta(carta: str, titulo: str) -> str:
    padrao = re.compile(rf"^##\s+{re.escape(titulo)}\b[^\n]*\n(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL)
    encontrado = padrao.search(carta)
    return encontrado.group(1) if encontrado else ""


def _sem_titulo(texto: str) -> str:
    """Remove a primeira linha `# Título` de uma camada ao concatená-la no arquivo do setor."""
    linhas = texto.splitlines()
    while linhas and not linhas[0].strip():
        linhas.pop(0)
    if linhas and linhas[0].startswith("# "):
        linhas.pop(0)
    return "\n".join(linhas).strip("\n")


def _rebaixar_titulos(texto: str) -> str:
    """Empurra `# Título` para `## Título` e `## X` para `### X` ao concatenar camadas."""
    linhas = []
    for linha in texto.splitlines():
        if linha.startswith("#"):
            linha = "#" + linha
        linhas.append(linha)
    return "\n".join(linhas)
