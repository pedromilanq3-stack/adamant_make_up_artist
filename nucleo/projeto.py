"""O Projeto: manifesto, setores, dossiês, diário de alterações e os pacotes enviados ao GPT.

Regras que este módulo faz cumprir por construção:

- um bloco de aprendizado só escreve no setor que o emitiu (ErroDeIsolamento);
- a Camada 1 de cada setor é travada por hash e só muda com autorização de Milan;
- nada é apagado: correções acrescentam e marcam o anterior como superado;
- nenhuma alteração é silenciosa: toda mudança entra no diário com versão anterior,
  versão nova, diferença, motivo, responsável e autorização, e a versão anterior fica
  guardada em versoes/ para reversão;
- conhecimento cruza setores apenas por dossiê mínimo; dossiê sensível ou amplo
  espera autorização de Milan antes de poder ser usado;
- setores nascem Propostos, geram o evento NOVO_SETOR para ATLAS e só operam depois de
  Aprovado → Piloto → Ativo, cada passo autorizado por Milan; ATLAS pode colocar um
  setor em Quarentena preventiva, mas só Milan o tira de lá.
"""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .diario import NAO_INFORMADO, Diario
from .patch import BlocoDeAprendizado, BlocoDoAtlas, ErroDePatch, Secao
from .registros import Registro, parse_registros, proximo_id, render_registros
from .setor import (
    CAMADAS, CAMPOS_OBRIGATORIOS, PREFIXOS, SECOES_DA_CAMADA_1, STATUS_SUPERADO, ErroDeValidacao,
    Setor, hash_texto,
)

ESTADOS_DE_SETOR = ("Proposto", "Aprovado", "Piloto", "Ativo", "Limitado", "Quarentena",
                    "Pausado", "Encerrado")
TRANSICOES = {
    "aprovar": ("Proposto", "Aprovado"),
    "piloto": ("Aprovado", "Piloto"),
    "ativar": ("Piloto", "Ativo"),
    "reativar": (("Pausado", "Quarentena"), "Ativo"),
    "limitar": ("Ativo", "Limitado"),
    "liberar": ("Limitado", "Ativo"),
    "quarentena": (("Piloto", "Ativo", "Limitado"), "Quarentena"),
    "pausar": (("Ativo", "Limitado"), "Pausado"),
    "encerrar": (("Piloto", "Ativo", "Limitado", "Quarentena", "Pausado"), "Encerrado"),
}
ESTADOS_OPERANTES = {"Piloto", "Ativo", "Limitado"}
SECOES_DA_CARTA = (
    "Nome", "Missão", "Problema que resolve", "Decisões sob sua responsabilidade",
    "Fora do escopo", "Atividades proibidas", "Cérebro e método de análise",
    "Agentes necessários", "Ferramentas permitidas", "Dados de entrada",
    "Entradas e entregáveis", "Métricas", "Dependências", "Riscos", "Custo estimado",
    "Orçamento ou limite de consumo", "Relações com outros setores",
    "Condição de suspensão ou encerramento", "Responsável pela criação",
)
CAMPOS_DO_DOSSIE = ("para", "fato", "fonte", "confianca", "restricao", "pergunta")
ARQUIVO_MANIFESTO = "manifesto.json"
ARQUIVO_INSTRUCOES = "ADENDO_HARVEY.md"
ARQUIVO_PROTOCOLO = "PROTOCOLO_DO_CEREBRO.md"
PASTA_ATLAS = "atlas"
ARQUIVO_INSTRUCOES_ATLAS = "INSTRUCOES_ATLAS.md"
ARQUIVO_NUCLEO_ATLAS = "NUCLEO_ATLAS.md"
LIMITE_INSTRUCOES = 8000
LIMITE_ADENDO = 4500  # o adendo é somado às instruções que o Harvey de Milan já tem
AGENTE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)


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


def agentes_da_camada1(camada1: str) -> list[str]:
    secao = _secao(camada1, "Agentes")
    return [linha.split("—")[0].strip() for linha in AGENTE.findall(secao)]


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
        manifesto.setdefault("atlas", {})
        return cls(raiz, manifesto)

    def salvar_manifesto(self) -> None:
        texto = json.dumps(self.manifesto, ensure_ascii=False, indent=2) + "\n"
        (self.raiz / ARQUIVO_MANIFESTO).write_text(texto, encoding="utf-8")

    @property
    def diario(self) -> Diario:
        return Diario(self.raiz)

    @property
    def pasta_setores(self) -> Path:
        return self.raiz / "setores"

    @property
    def pasta_dossies(self) -> Path:
        return self.raiz / "dossies"

    @property
    def pasta_upload(self) -> Path:
        """Sala do Harvey que Milan já tem: adendo de integração + arquivos."""
        return self.raiz / "upload_harvey"

    @property
    def pasta_upload_setores(self) -> Path:
        """Uma sala por setor operante."""
        return self.raiz / "upload_setores"

    @property
    def pasta_atlas(self) -> Path:
        return self.raiz / PASTA_ATLAS

    def entrada(self, id_setor: str) -> dict:
        try:
            return self.manifesto["setores"][id_setor]
        except KeyError:
            raise ErroDeValidacao(f"setor {id_setor} não existe no manifesto") from None

    def pasta_do_setor(self, id_setor: str) -> Path:
        return self.pasta_setores / self.entrada(id_setor)["pasta"]

    def setor(self, id_setor: str) -> Setor:
        return Setor.carregar(id_setor, self.pasta_do_setor(id_setor))

    def setores(self) -> list[str]:
        return sorted(self.manifesto["setores"])

    def setores_com_camadas(self) -> list[str]:
        return [s for s in self.setores() if self.entrada(s)["status"] != "Proposto"]

    def versao_de(self, id_setor: str) -> int:
        return int(self.entrada(id_setor).get("versao", 0))

    def hash_do_setor(self, id_setor: str) -> str:
        pasta = self.pasta_do_setor(id_setor)
        partes = []
        for nome in sorted(p.name for p in pasta.iterdir() if p.is_file()):
            partes.append(nome + "\n" + (pasta / nome).read_text(encoding="utf-8"))
        return hash_texto("\n".join(partes))

    def rotulo_de_versao(self, id_setor: str) -> str:
        return f"v{self.versao_de(id_setor):03d} ({self.hash_do_setor(id_setor)[:12]})"

    def hash_nucleo_atlas(self) -> str | None:
        caminho = self.pasta_atlas / ARQUIVO_NUCLEO_ATLAS
        if not caminho.exists():
            return None
        return hash_texto(caminho.read_text(encoding="utf-8"))

    # ------------------------------------------------------------- validar
    def validar(self) -> list[str]:
        problemas: list[str] = []
        for arquivo, limite in ((ARQUIVO_INSTRUCOES, LIMITE_ADENDO),
                                (f"{PASTA_ATLAS}/{ARQUIVO_INSTRUCOES_ATLAS}", LIMITE_INSTRUCOES)):
            caminho = self.raiz / arquivo
            if not caminho.exists():
                problemas.append(f"falta {arquivo}")
            elif len(caminho.read_text(encoding="utf-8")) > limite:
                problemas.append(
                    f"{arquivo} passa de {limite} caracteres; o campo de instruções do Projeto pode "
                    "cortar o texto"
                )
        for arquivo in (ARQUIVO_PROTOCOLO, f"{PASTA_ATLAS}/{ARQUIVO_NUCLEO_ATLAS}"):
            if not (self.raiz / arquivo).exists():
                problemas.append(f"falta {arquivo}")
        trava_atlas = self.manifesto["atlas"].get("trava_nucleo")
        hash_atlas = self.hash_nucleo_atlas()
        if hash_atlas and not trava_atlas:
            problemas.append("ATLAS: núcleo não está travado (use 'travar ATLAS')")
        elif hash_atlas and trava_atlas != hash_atlas:
            problemas.append("ATLAS: núcleo foi alterado sem autorização (hash difere da trava)")
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
            if not (self.raiz / "modelos" / "instrucoes_de_setor.md").exists() and id_setor == self.setores()[0]:
                problemas.append("falta modelos/instrucoes_de_setor.md (sala de cada setor)")
            if entrada.get("status") in ESTADOS_OPERANTES and not self.diario.versoes(id_setor):
                problemas.append(f"{id_setor}: sem versão guardada para reversão (use 'versoes guardar')")
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

    # ------------------------------------------------------------- versões
    def guardar_versao(self, id_setor: str) -> Path:
        """Guarda os arquivos atuais do setor como baseline da versão corrente."""
        entrada = self.entrada(id_setor)
        numero = int(entrada.get("versao", 0))
        if numero == 0:
            numero = 1
            entrada["versao"] = 1
            self.salvar_manifesto()
        pasta = self.pasta_do_setor(id_setor)
        return self.diario.guardar_versao(id_setor, numero, sorted(p for p in pasta.iterdir() if p.is_file()))

    def _antes_de_mudar(self, id_setor: str) -> str:
        """Garante baseline da versão atual (se faltar) e devolve o rótulo da versão anterior.

        Como cada versão é guardada logo depois de nascer, uma edição manual feita entre
        duas operações não contamina a baseline: ela já existia antes da edição.
        """
        if self.entrada(id_setor)["status"] != "Proposto":
            self.guardar_versao(id_setor)
        return self.rotulo_de_versao(id_setor)

    def _depois_de_mudar(self, id_setor: str, *, operacao: str, diferenca: str, motivo: str,
                         responsavel: str, autorizacao: str, hoje: date, versao_anterior: str,
                         **extras: str) -> Registro:
        entrada = self.entrada(id_setor)
        entrada["versao"] = int(entrada.get("versao", 0)) + 1
        entrada["alterado_em"] = hoje.isoformat()
        entrada["ultima_autorizacao"] = autorizacao
        self.salvar_manifesto()
        if entrada["status"] != "Proposto":
            self.guardar_versao(id_setor)  # a baseline de cada versão é o estado dessa versão
        anterior = versao_anterior.split(" ")[0]
        return self.diario.registrar_alteracao(
            componente=id_setor, operacao=operacao, versao_anterior=versao_anterior,
            versao_nova=self.rotulo_de_versao(id_setor), diferenca=diferenca, motivo=motivo,
            responsavel=responsavel, autorizacao=autorizacao, hoje=hoje,
            reversao=f"nucleo versoes reverter {id_setor} {anterior} --autorizado-por-milan",
            **extras,
        )

    def reverter(self, id_setor: str, versao: str, autorizado_por_milan: bool, motivo: str = "",
                 hoje: date | None = None) -> Registro:
        exige_milan(autorizado_por_milan, f"reverter {id_setor} para {versao}")
        hoje = hoje or date.today()
        numero = int(versao.lstrip("v"))
        anterior = self._antes_de_mudar(id_setor)
        restaurados = self.diario.restaurar_versao(id_setor, numero, self.pasta_do_setor(id_setor))
        setor = self.setor(id_setor)
        entrada = self.entrada(id_setor)
        entrada["trava_camada1"] = setor.hash_camada1()
        return self._depois_de_mudar(
            id_setor, operacao="reversao", diferenca=f"restaurados {len(restaurados)} arquivo(s) de v{numero:03d}",
            motivo=motivo or f"reversão para v{numero:03d}", responsavel="Milan",
            autorizacao="Milan (--autorizado-por-milan)", hoje=hoje, versao_anterior=anterior,
            teste="rode 'nucleo validar' após a reversão",
        )

    # ------------------------------------------------------------- travar
    def travar(self, id_setor: str, autorizado_por_milan: bool, motivo: str = "",
               hoje: date | None = None) -> str:
        exige_milan(autorizado_por_milan, f"travar a camada 1 de {id_setor}")
        hoje = hoje or date.today()
        if id_setor.upper() == "ATLAS":
            return self._travar_atlas(motivo, hoje)
        setor = self.setor(id_setor)
        problemas = [p for p in setor.validar() if "/camada1" in p]
        if problemas:
            raise ErroDeValidacao("; ".join(problemas))
        entrada = self.entrada(id_setor)
        trava_antiga = entrada.get("trava_camada1")
        nova = setor.hash_camada1()
        if trava_antiga == nova:
            return nova
        versao_anterior = self._antes_de_mudar(id_setor)
        agentes_antes = self._agentes_da_versao_anterior(id_setor)
        agentes_depois = agentes_da_camada1(setor.camada1)
        entrada["trava_camada1"] = nova
        entrada["camada1_travada_em"] = hoje.isoformat()
        diferenca = f"camada 1: {trava_antiga[:12] if trava_antiga else 'sem trava'} → {nova[:12]}"
        novos = [a for a in agentes_depois if a not in agentes_antes]
        removidos = [a for a in agentes_antes if a not in agentes_depois]
        if novos or removidos:
            diferenca += f"; agentes novos: {novos or 'nenhum'}; removidos: {removidos or 'nenhum'}"
        self._depois_de_mudar(
            id_setor, operacao="travar_camada1", diferenca=diferenca, motivo=motivo,
            responsavel="Milan", autorizacao="Milan (--autorizado-por-milan)", hoje=hoje,
            versao_anterior=versao_anterior,
        )
        if trava_antiga:
            self.diario.acrescentar("eventos", {
                "evento": "MUDANCA_DE_NUCLEO", "componente": id_setor, "diferenca": diferenca,
                "agentes_atuais": ", ".join(agentes_depois) or "nenhum",
                "autorizacao_de_milan": f"concedida em {hoje.isoformat()}", "data": hoje.isoformat(),
                "status": "pendente_para_atlas",
            })
        return nova

    def _agentes_da_versao_anterior(self, id_setor: str) -> list[str]:
        versoes = self.diario.versoes(id_setor)
        if not versoes:
            return []
        caminho = versoes[-1] / CAMADAS[1]
        if not caminho.exists():
            return []
        return agentes_da_camada1(caminho.read_text(encoding="utf-8"))

    def _travar_atlas(self, motivo: str, hoje: date) -> str:
        novo = self.hash_nucleo_atlas()
        if novo is None:
            raise ErroDeValidacao(f"falta {PASTA_ATLAS}/{ARQUIVO_NUCLEO_ATLAS}")
        antigo = self.manifesto["atlas"].get("trava_nucleo")
        if antigo == novo:
            return novo
        versao = int(self.manifesto["atlas"].get("versao", 0))
        if versao:
            self.diario.guardar_versao("ATLAS", versao, [self.pasta_atlas / ARQUIVO_NUCLEO_ATLAS,
                                                         self.pasta_atlas / ARQUIVO_INSTRUCOES_ATLAS])
        self.manifesto["atlas"].update({
            "trava_nucleo": novo, "versao": versao + 1, "travado_em": hoje.isoformat(),
            "ultima_autorizacao": "Milan (--autorizado-por-milan)",
        })
        self.salvar_manifesto()
        self.diario.guardar_versao("ATLAS", versao + 1, [self.pasta_atlas / ARQUIVO_NUCLEO_ATLAS,
                                                         self.pasta_atlas / ARQUIVO_INSTRUCOES_ATLAS])
        self.diario.registrar_alteracao(
            componente="ATLAS", operacao="travar_nucleo",
            versao_anterior=f"v{versao:03d} ({antigo[:12] if antigo else 'sem trava'})",
            versao_nova=f"v{versao + 1:03d} ({novo[:12]})", diferenca="núcleo de ATLAS retravado",
            motivo=motivo, responsavel="Milan", autorizacao="Milan (--autorizado-por-milan)", hoje=hoje,
        )
        return novo

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
        versao_anterior = self._antes_de_mudar(bloco.setor)
        setor.salvar()
        for dossie in pendentes:
            self._gravar_dossie(dossie)
        self._depois_de_mudar(
            bloco.setor, operacao="aprendizado", diferenca="; ".join(relato),
            motivo=f"bloco de aprendizado de {bloco.data}", responsavel=bloco.emitido_por,
            autorizacao="Milan (--autorizado-por-milan)" if autorizado_por_milan
            else "não exigida: memória do próprio setor", hoje=hoje, versao_anterior=versao_anterior,
        )
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

    # ------------------------------------------------------- bloco do ATLAS
    def aplicar_atlas(self, bloco: BlocoDoAtlas, hoje: date | None = None) -> list[str]:
        """Registra o que ATLAS devolveu: status, alertas, recomendações, quarentenas."""
        hoje = hoje or date.today()
        relato: list[str] = []
        for secao in bloco.secoes:
            campos = dict(secao.campos)
            campos["data"] = hoje.isoformat()
            campos["emitido_por"] = "ATLAS"
            if secao.tipo == "status":
                status = campos.get("status", "").upper()
                if status not in {"ÍNTEGRO", "INTEGRO", "ATENÇÃO", "ATENCAO", "BLOQUEADO"}:
                    raise ErroDePatch("'## status' precisa de status ÍNTEGRO, ATENÇÃO ou BLOQUEADO")
                campos["status"] = status
                campos["tipo"] = "status_de_integridade"
                novo = self.diario.acrescentar("alertas", campos)
                self.manifesto["atlas"]["ultimo_status"] = {"status": status, "em": hoje.isoformat(),
                                                             "registro": novo.id}
                self.salvar_manifesto()
                relato.append(f"{novo.id}: status {status} registrado")
            elif secao.tipo in ("alerta", "auditoria"):
                campos["tipo"] = secao.tipo
                campos.setdefault("status", "aberto")
                novo = self.diario.acrescentar("alertas", campos)
                relato.append(f"{novo.id}: {secao.tipo} registrado ({campos.get('componente', 'sistema')})")
            elif secao.tipo == "recomendacao":
                faltando = [c for c in ("conteudo", "impacto", "urgencia", "confianca", "esforco",
                                        "custo", "risco", "reversibilidade") if not campos.get(c)]
                if faltando:
                    raise ErroDePatch(f"'## recomendacao' sem os campos: {', '.join(faltando)}")
                campos.setdefault("status", "aguardando_milan")
                novo = self.diario.acrescentar("recomendacoes", campos)
                relato.append(f"{novo.id}: recomendação registrada (aguarda Milan)")
            elif secao.tipo == "quarentena":
                motivo = campos.get("motivo", "")
                if not motivo:
                    raise ErroDePatch("'## quarentena Snn' precisa de 'motivo'")
                self.transicionar(secao.alvo, "quarentena", False, por="ATLAS", motivo=motivo, hoje=hoje)
                campos.update({"tipo": "quarentena", "componente": secao.alvo, "status": "aberto",
                               "problema": motivo, "recomendacao": campos.get(
                                   "recomendacao", f"Milan decide: reativar ou encerrar {secao.alvo}")})
                novo = self.diario.acrescentar("alertas", campos)
                relato.append(f"{secao.alvo} em Quarentena preventiva ({novo.id}); só Milan libera")
            elif secao.tipo == "evento_recebido":
                evento = self.diario.buscar("eventos", secao.alvo)
                if evento is None:
                    raise ErroDePatch(f"evento {secao.alvo} não existe")
                evento.set("status", "recebido_por_atlas")
                evento.set("recebido_em", hoje.isoformat())
                if campos.get("parecer"):
                    evento.set("parecer_de_atlas", campos["parecer"])
                self.diario.atualizar("eventos", evento)
                relato.append(f"{secao.alvo} marcado como recebido por ATLAS")
            else:
                raise ErroDePatch(f"seção desconhecida no bloco atlas: {secao.tipo}")
        return relato

    def decidir_recomendacao(self, id_rec: str, decisao: str, autorizado_por_milan: bool,
                             hoje: date | None = None) -> Registro:
        exige_milan(autorizado_por_milan, f"decidir a recomendação {id_rec}")
        hoje = hoje or date.today()
        if decisao not in {"aceitar", "recusar"}:
            raise ValueError("decisão deve ser 'aceitar' ou 'recusar'")
        registro = self.diario.buscar("recomendacoes", id_rec)
        if registro is None:
            raise ErroDeValidacao(f"recomendação {id_rec} não existe")
        registro.set("status", "aceita" if decisao == "aceitar" else "recusada")
        registro.set("decidido_por", "Milan")
        registro.set("decidido_em", hoje.isoformat())
        self.diario.atualizar("recomendacoes", registro)
        return registro

    def fechar_alerta(self, id_alerta: str, autorizado_por_milan: bool, resolucao: str,
                      hoje: date | None = None) -> Registro:
        exige_milan(autorizado_por_milan, f"fechar o alerta {id_alerta}")
        hoje = hoje or date.today()
        registro = self.diario.buscar("alertas", id_alerta)
        if registro is None:
            raise ErroDeValidacao(f"alerta {id_alerta} não existe")
        registro.set("status", "fechado")
        registro.set("resolucao", resolucao or NAO_INFORMADO)
        registro.set("fechado_em", hoje.isoformat())
        self.diario.atualizar("alertas", registro)
        return registro

    def registrar_custo(self, componente: str, valor: str, unidade: str, descricao: str,
                        hoje: date | None = None) -> Registro:
        hoje = hoje or date.today()
        if componente != "sistema" and componente not in self.manifesto["setores"] and componente != "ATLAS":
            raise ErroDeValidacao(f"componente {componente} desconhecido (use Snn, ATLAS ou sistema)")
        float(valor.replace(",", "."))
        return self.diario.acrescentar("custos", {
            "componente": componente, "valor": valor, "unidade": unidade,
            "descricao": descricao or NAO_INFORMADO, "informado_por": "Milan", "data": hoje.isoformat(),
        })

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

    def decidir_dossie(self, id_dossie: str, decisao: str, autorizado_por_milan: bool,
                       hoje: date | None = None) -> Registro:
        exige_milan(autorizado_por_milan, f"decidir o dossiê {id_dossie}")
        hoje = hoje or date.today()
        if decisao not in {"autorizar", "recusar"}:
            raise ValueError("decisão deve ser 'autorizar' ou 'recusar'")
        dossie = self.dossie(id_dossie)
        if dossie is None:
            raise ErroDeValidacao(f"dossiê {id_dossie} não existe")
        if dossie.get("status") != "pendente":
            raise ErroDeValidacao(f"{id_dossie} não está pendente (status: {dossie.get('status')})")
        dossie.set("status", "autorizado" if decisao == "autorizar" else "recusado")
        dossie.set("decidido_por", "Milan")
        dossie.set("decidido_em", hoje.isoformat())
        self._gravar_dossie(dossie)
        self.diario.registrar_alteracao(
            componente="DOSSIES", operacao=f"dossie_{decisao}", versao_anterior=f"{id_dossie} pendente",
            versao_nova=f"{id_dossie} {dossie.get('status')}",
            diferenca=f"{dossie.get('de')} → {dossie.get('para')}: {dossie.get('fato')}",
            motivo=NAO_INFORMADO, responsavel="Milan", autorizacao="Milan (--autorizado-por-milan)", hoje=hoje,
        )
        return dossie

    # ---------------------------------------------------- ciclo de vida
    def propor_setor(self, id_setor: str, carta: str, hoje: date | None = None) -> Path:
        hoje = hoje or date.today()
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
        nome_bruto = _secao(carta, "Nome").strip()
        nome = nome_bruto.splitlines()[0] if nome_bruto else id_setor
        pasta = f"{id_setor}_{slug(nome)}"
        destino = self.pasta_setores / pasta
        destino.mkdir(parents=True, exist_ok=False)
        (destino / "carta.md").write_text(carta.rstrip("\n") + "\n", encoding="utf-8")
        self.manifesto["setores"][id_setor] = {
            "nome": nome, "pasta": pasta, "status": "Proposto", "versao": 0,
            "proposto_em": hoje.isoformat(),
            "responsavel_pela_criacao": _secao(carta, "Responsável pela criação").strip() or NAO_INFORMADO,
        }
        self.salvar_manifesto()
        evento = self._evento_novo_setor(id_setor, carta, hoje)
        self.manifesto["setores"][id_setor]["evento"] = evento.id
        self.salvar_manifesto()
        self.diario.registrar_alteracao(
            componente=id_setor, operacao="propor_setor", versao_anterior="inexistente",
            versao_nova="Proposto (carta)", diferenca=f"carta registrada; evento {evento.id} emitido para ATLAS",
            motivo=_secao(carta, "Problema que resolve").strip() or NAO_INFORMADO,
            responsavel=self.manifesto["setores"][id_setor]["responsavel_pela_criacao"],
            autorizacao="pendente (Milan ainda não aprovou)", hoje=hoje,
        )
        return destino

    def _evento_novo_setor(self, id_setor: str, carta: str, hoje: date) -> Registro:
        def sec(titulo: str) -> str:
            return " ".join(_secao(carta, titulo).split()) or NAO_INFORMADO
        return self.diario.acrescentar("eventos", {
            "evento": "NOVO_SETOR", "componente": id_setor, "nome": sec("Nome"),
            "missao": sec("Missão"), "problema_que_resolve": sec("Problema que resolve"),
            "escopo_permitido": sec("Decisões sob sua responsabilidade"),
            "atividades_proibidas": sec("Atividades proibidas") + " | fora do escopo: " + sec("Fora do escopo"),
            "cerebro_ou_metodo": sec("Cérebro e método de análise"),
            "agentes_internos": sec("Agentes necessários"),
            "prompt_principal_e_versao": f"camada1_nucleo.md gerada da carta na aprovação (versão inicial v001)",
            "ferramentas_solicitadas": sec("Ferramentas permitidas"),
            "dados_de_entrada": sec("Dados de entrada"), "entregaveis": sec("Entradas e entregáveis"),
            "metricas": sec("Métricas"), "dependencias": sec("Dependências"), "riscos": sec("Riscos"),
            "orcamento_ou_limite": sec("Orçamento ou limite de consumo"),
            "condicao_de_parada": sec("Condição de suspensão ou encerramento"),
            "responsavel_pela_criacao": sec("Responsável pela criação"),
            "autorizacao_de_milan": "pendente", "data": hoje.isoformat(), "status": "pendente_para_atlas",
        })

    def transicionar(self, id_setor: str, acao: str, autorizado_por_milan: bool, por: str = "Milan",
                     motivo: str = "", hoje: date | None = None) -> str:
        hoje = hoje or date.today()
        if acao not in TRANSICOES:
            raise ValueError(f"ação desconhecida '{acao}'; use {sorted(TRANSICOES)}")
        if acao == "quarentena":
            if por not in {"Milan", "ATLAS"}:
                raise ErroDeAutorizacao("quarentena preventiva só por ATLAS ou Milan")
            if not motivo:
                raise ErroDeValidacao("quarentena exige --motivo com a causa, que vai imediatamente a Milan")
            autorizacao = "Milan (--autorizado-por-milan)" if autorizado_por_milan else \
                f"{por}: suspensão preventiva; causa apresentada a Milan"
        else:
            exige_milan(autorizado_por_milan, f"{acao} o setor {id_setor}")
            por = "Milan"
            autorizacao = "Milan (--autorizado-por-milan)"
        entrada = self.entrada(id_setor)
        origens, destino = TRANSICOES[acao]
        origens = (origens,) if isinstance(origens, str) else origens
        if entrada["status"] not in origens:
            raise ErroDeValidacao(
                f"{id_setor} está '{entrada['status']}'; '{acao}' exige {' ou '.join(origens)}"
            )
        anterior = entrada["status"]
        versao_anterior = f"{anterior}" if anterior == "Proposto" else self._antes_de_mudar(id_setor)
        if anterior == "Quarentena":
            for alerta in self.diario.ler("alertas"):
                if alerta.get("tipo") == "quarentena" and alerta.get("componente") == id_setor \
                        and alerta.get("status") == "aberto":
                    alerta.set("status", "fechado")
                    alerta.set("resolucao", f"Milan decidiu: {acao} ({motivo or 'sem motivo informado'})")
                    alerta.set("fechado_em", hoje.isoformat())
                    self.diario.atualizar("alertas", alerta)
        if acao == "aprovar":
            self._criar_camadas_da_carta(id_setor, entrada, hoje)
            entrada["versao"] = 1
            evento_id = entrada.get("evento")
            evento = self.diario.buscar("eventos", evento_id) if evento_id else None
            if evento is not None:
                evento.set("autorizacao_de_milan", f"concedida em {hoje.isoformat()}")
                self.diario.atualizar("eventos", evento)
        entrada["status"] = destino
        if motivo:
            entrada["motivo_do_status"] = motivo
        elif "motivo_do_status" in entrada:
            del entrada["motivo_do_status"]
        entrada.setdefault("historico", []).append(
            {"de": anterior, "para": destino, "em": hoje.isoformat(), "por": por,
             **({"motivo": motivo} if motivo else {})}
        )
        self.salvar_manifesto()
        if acao == "aprovar":
            setor = self.setor(id_setor)
            entrada["trava_camada1"] = setor.hash_camada1()
            entrada["camada1_travada_em"] = hoje.isoformat()
            self.salvar_manifesto()
            self.guardar_versao(id_setor)
            self.diario.registrar_alteracao(
                componente=id_setor, operacao="aprovar", versao_anterior="Proposto (carta)",
                versao_nova=self.rotulo_de_versao(id_setor),
                diferenca="cinco camadas criadas a partir da carta; camada 1 travada",
                motivo=motivo, responsavel="Milan", autorizacao=autorizacao, hoje=hoje,
                teste="piloto controlado antes de ativar",
                reversao=f"nucleo setor encerrar {id_setor} --autorizado-por-milan",
            )
            return destino
        self._depois_de_mudar(
            id_setor, operacao=acao, diferenca=f"status: {anterior} → {destino}", motivo=motivo,
            responsavel=por, autorizacao=autorizacao, hoje=hoje, versao_anterior=versao_anterior,
        )
        return destino

    def _criar_camadas_da_carta(self, id_setor: str, entrada: dict, hoje: date) -> None:
        pasta = self.pasta_setores / entrada["pasta"]
        carta = (pasta / "carta.md").read_text(encoding="utf-8")
        nome = entrada["nome"]
        mapa = {
            "Missão": ("Missão",),
            "Responsabilidade": ("Decisões sob sua responsabilidade",),
            "Limites": ("Fora do escopo", "Atividades proibidas"),
            "Método de análise": ("Cérebro e método de análise",),
            "Ferramentas permitidas": ("Ferramentas permitidas",),
            "Formato de saída": ("Entradas e entregáveis", "Dados de entrada"),
            "Métricas": ("Métricas",),
            "Condições de parada": ("Condição de suspensão ou encerramento", "Orçamento ou limite de consumo"),
            "Agentes": ("Agentes necessários",),
        }
        partes = [f"# {id_setor} — {nome}", "",
                  "Camada 1 — Núcleo travado. Somente Milan altera este arquivo; depois de alterar, "
                  f"execute `nucleo travar {id_setor} --autorizado-por-milan`.", ""]
        for secao in SECOES_DA_CAMADA_1:
            partes.append(f"## {secao}")
            partes.append("")
            texto = "\n\n".join(t for t in (_secao(carta, s).strip() for s in mapa[secao]) if t)
            partes.append(texto or "(a definir por Milan)")
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
            "bloqueios": "nenhum", "autorizacoes_pendentes": "nenhuma", "atualizado_em": hoje.isoformat(),
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
        atlas = [
            f"{a.id}: {a.get('tipo')} aberto em {a.get('componente', 'sistema')} — {a.get('problema', a.get('conteudo', ''))}"
            for a in self.diario.ler("alertas") if a.get("status") == "aberto"
        ] + [
            f"{r.id}: recomendação aguarda decisão de Milan — {r.get('conteudo')}"
            for r in self.diario.ler("recomendacoes") if r.get("status") == "aguardando_milan"
        ] + [
            f"{e.id}: evento {e.get('evento')} de {e.get('componente')} ainda não recebido por ATLAS"
            for e in self.diario.ler("eventos") if e.get("status") == "pendente_para_atlas"
        ]
        if atlas:
            resultado["atlas"] = atlas
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
        for origem, nome in ((ARQUIVO_INSTRUCOES, "00_ADENDO_PARA_O_SEU_HARVEY.md"),
                             (ARQUIVO_PROTOCOLO, "01_PROTOCOLO_DO_CEREBRO.md")):
            gerados.append(destino / nome)
            shutil.copyfile(self.raiz / origem, destino / nome)
        gerados.append(destino / "02_MANIFESTO.md")
        (destino / "02_MANIFESTO.md").write_text(self._manifesto_md(hoje), encoding="utf-8")
        avisos = self._avisos_de_atlas_md()
        if avisos:
            gerados.append(destino / "03_AVISOS_DE_ATLAS.md")
            (destino / "03_AVISOS_DE_ATLAS.md").write_text(avisos, encoding="utf-8")
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
        gerados.extend(self._empacotar_salas_dos_setores(hoje, avisos))
        return gerados

    def _empacotar_salas_dos_setores(self, hoje: date, avisos: str) -> list[Path]:
        """Cada setor tem a própria sala: instruções geradas da Camada 1 + o seu cérebro."""
        raiz = self.pasta_upload_setores
        if raiz.exists():
            shutil.rmtree(raiz)
        gerados: list[Path] = []
        modelo = (self.raiz / "modelos" / "instrucoes_de_setor.md").read_text(encoding="utf-8")
        for id_setor in self.setores_com_camadas():
            entrada = self.entrada(id_setor)
            destino = raiz / id_setor
            destino.mkdir(parents=True)
            nome_arquivo = f"{id_setor}_{slug(entrada['nome']).upper()}.md"
            instrucoes = self.instrucoes_do_setor(id_setor, modelo, nome_arquivo)
            if len(instrucoes) > LIMITE_INSTRUCOES:
                raise ErroDeValidacao(
                    f"instruções da sala de {id_setor} passam de {LIMITE_INSTRUCOES} caracteres; "
                    "encurte Missão, Limites ou Agentes na Camada 1"
                )
            (destino / f"00_INSTRUCOES_{id_setor}.md").write_text(instrucoes, encoding="utf-8")
            gerados.append(destino / f"00_INSTRUCOES_{id_setor}.md")
            shutil.copyfile(self.raiz / ARQUIVO_PROTOCOLO, destino / "01_PROTOCOLO_DO_CEREBRO.md")
            gerados.append(destino / "01_PROTOCOLO_DO_CEREBRO.md")
            (destino / "02_MANIFESTO.md").write_text(self._manifesto_md(hoje), encoding="utf-8")
            gerados.append(destino / "02_MANIFESTO.md")
            if avisos:
                (destino / "03_AVISOS_DE_ATLAS.md").write_text(avisos, encoding="utf-8")
                gerados.append(destino / "03_AVISOS_DE_ATLAS.md")
            (destino / nome_arquivo).write_text(
                self._setor_md(id_setor, entrada, self.pasta_do_setor(id_setor), hoje), encoding="utf-8")
            gerados.append(destino / nome_arquivo)
            proprios = [d for d in self.dossies()
                        if id_setor in (d.get("de"), d.get("para")) and d.get("status") in {"autorizado", "entregue"}]
            if proprios:
                (destino / "90_DOSSIES.md").write_text(render_registros(
                    f"# Dossiês autorizados que envolvem {id_setor}\n\nÚnico conhecimento de outros setores "
                    "que este setor pode usar, dentro da restrição de uso de cada dossiê.", proprios),
                    encoding="utf-8")
                gerados.append(destino / "90_DOSSIES.md")
        return gerados

    def instrucoes_do_setor(self, id_setor: str, modelo: str, nome_arquivo: str) -> str:
        setor = self.setor(id_setor)
        camada1 = setor.camada1
        agentes = []
        for nome in agentes_da_camada1(camada1):
            linha = next((l for l in AGENTE.findall(_secao(camada1, "Agentes")) if l.startswith(nome)), nome)
            agentes.append(f"- {linha}")
        estado = setor.estado
        inicializacao = ("## Inicialização\n"
                         "Ao receber \"iniciar\" ou a primeira ordem de Harvey, não apresente plano completo. "
                         f"Siga a próxima ação do ESTADO da Camada 5: {estado.get('proxima_acao')}")
        return (modelo.replace("{ID}", id_setor).replace("{NOME}", setor.nome.split("—", 1)[-1].strip())
                .replace("{ARQUIVO_SETOR}", nome_arquivo)
                .replace("{MISSAO}", " ".join(_secao(camada1, "Missão").split()) or "(ver Camada 1)")
                .replace("{LIMITES}", " ".join(_secao(camada1, "Limites").split()) or "(ver Camada 1)")
                .replace("{AGENTES}", "\n".join(agentes) or "- (nenhum agente definido na Camada 1)")
                .replace("{INICIALIZACAO}", inicializacao))

    def _avisos_de_atlas_md(self) -> str:
        alertas = [a for a in self.diario.ler("alertas") if a.get("status") == "aberto"]
        recomendacoes = [r for r in self.diario.ler("recomendacoes") if r.get("status") == "aceita"]
        quarentenas = [s for s in self.setores() if self.entrada(s)["status"] in {"Quarentena", "Limitado"}]
        if not (alertas or recomendacoes or quarentenas):
            return ""
        linhas = ["# Avisos de ATLAS para Harvey e os setores", "",
                  "ATLAS governa a estrutura; estes avisos são dados a considerar, não ordens acima de Milan.", ""]
        for id_setor in quarentenas:
            entrada = self.entrada(id_setor)
            linhas.append(f"- {id_setor} está em **{entrada['status']}**: {entrada.get('motivo_do_status', NAO_INFORMADO)}")
        for alerta in alertas:
            linhas.append(f"- {alerta.id} ({alerta.get('tipo')}, {alerta.get('componente', 'sistema')}): "
                          f"{alerta.get('problema', alerta.get('conteudo', ''))} → {alerta.get('recomendacao', '')}")
        for rec in recomendacoes:
            linhas.append(f"- {rec.id} (aceita por Milan): {rec.get('conteudo')}")
        return "\n".join(linhas) + "\n"

    def _manifesto_md(self, hoje: date) -> str:
        linhas = ["# Manifesto do Projeto", "", f"Gerado em {hoje.isoformat()} pelo Núcleo. "
                  "Se um arquivo de setor no Projeto tiver hash diferente do listado aqui, ele está "
                  "desatualizado: avise Milan antes de confiar nele.", "", "## Setores", "",
                  "| Setor | Nome | Status | Versão | Hash da camada 1 | Fatos | Hipóteses | Lições |",
                  "|---|---|---|---|---|---|---|---|"]
        for id_setor in self.setores():
            entrada = self.entrada(id_setor)
            if entrada["status"] == "Proposto":
                linhas.append(f"| {id_setor} | {entrada['nome']} | Proposto | — | — | — | — | — |")
                continue
            setor = self.setor(id_setor)
            m = setor.metricas()
            linhas.append(
                f"| {id_setor} | {entrada['nome']} | {entrada['status']} | v{self.versao_de(id_setor):03d} | "
                f"{setor.hash_camada1()[:12]} | {m['fatos_vigentes']} | "
                f"{sum(m['hipoteses'].values())} | {sum(m['licoes_vigentes'].values())} |"
            )
        ultimo = self.manifesto["atlas"].get("ultimo_status")
        linhas += ["", "## ATLAS", "",
                   f"Último status de integridade emitido por ATLAS: "
                   f"{ultimo['status'] + ' em ' + ultimo['em'] if ultimo else 'nenhum ainda'}. "
                   "ATLAS opera em sala separada; Harvey não faz o trabalho de ATLAS."]
        linhas += ["", "## Pendências de revisão", ""]
        pendencias = self.pendencias(hoje)
        if not pendencias:
            linhas.append("Nenhuma pendência.")
        for chave, itens in pendencias.items():
            linhas.append(f"### {chave}")
            linhas.extend(f"- {item}" for item in itens)
            linhas.append("")
        linhas += ["", "## Regras de leitura", "",
                   "- Três salas: Harvey coordena e responde a Milan; cada setor trabalha por ordem de Harvey "
                   "e entrega a ele; ATLAS governa a estrutura. Ninguém fala pelo outro.",
                   "- Setor Proposto, Quarentena, Pausado ou Encerrado não opera nem recebe aprendizado. "
                   "Limitado opera com as restrições anotadas.",
                   "- Cada setor lê somente o próprio arquivo. Outro setor entra apenas por dossiê "
                   "autorizado (veja 90_DOSSIES.md, se existir).",
                   "- A Camada 1 é travada: nunca proponha alterá-la dentro de um bloco de aprendizado.",
                   "- Setor ou agente novo só existe depois do evento NOVO_SETOR registrado pelo Núcleo e da "
                   "aprovação de Milan."]
        return "\n".join(linhas) + "\n"

    def _setor_md(self, id_setor: str, entrada: dict, pasta: Path, hoje: date) -> str:
        setor = Setor.carregar(id_setor, pasta)
        titulos = {2: "Camada 2 — Fatos verificados", 3: "Camada 3 — Hipóteses",
                   4: "Camada 4 — Lições e resultados", 5: "Camada 5 — Estado atual"}
        restricao = f" Motivo: {entrada['motivo_do_status']}." if entrada.get("motivo_do_status") else ""
        partes = [f"<!-- {id_setor} · status: {entrada['status']} · versão v{self.versao_de(id_setor):03d} · "
                  f"hash camada 1: {setor.hash_camada1()[:12]} · gerado em {hoje.isoformat()} -->", "",
                  "# " + setor.nome, "", f"Status: **{entrada['status']}**.{restricao} Este arquivo é o cérebro "
                  f"completo do setor. A Camada 1 é travada (hash {setor.hash_camada1()[:12]}).", "",
                  "---", "", "## Camada 1 — Núcleo travado", "",
                  _rebaixar_titulos(_sem_titulo(setor.camada1))]
        for numero in (2, 3, 4, 5):
            texto = render_registros(_sem_titulo(setor.preambulos[numero]), setor.registros[numero])
            partes += ["", "---", "", f"## {titulos[numero]}", "", _rebaixar_titulos(texto)]
        return "\n".join(partes).rstrip("\n") + "\n"


def _secao(texto: str, titulo: str) -> str:
    padrao = re.compile(rf"^##\s+{re.escape(titulo)}\b[^\n]*\n(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL)
    encontrado = padrao.search(texto)
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
