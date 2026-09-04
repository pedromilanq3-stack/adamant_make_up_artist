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

from . import mente as mente_mod
from . import psique as psique_mod
from .diario import NAO_INFORMADO, Diario
from .patch import BlocoDeAprendizado, BlocoDoAtlas, ErroDePatch, Secao
from .registros import Registro, parse_registros, proximo_id, render_registros
from .setor import (
    CAMADAS, CAMPOS_OBRIGATORIOS, PREFIXOS, SECOES_DA_CAMADA_1, STATUS_SUPERADO, ErroDeValidacao,
    Setor, hash_texto, tipo_do_registro,
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
ARQUIVO_INSTRUCOES = "harvey/INSTRUCOES_HARVEY.md"
ARQUIVO_ADENDO = "ADENDO_HARVEY.md"
PASTA_HARVEY = "harvey"
HARVEY = "HARVEY"
BATMAN = "BATMAN"
NEX = "NEX"
# Personagens: componentes com sala própria e cérebro procedural, fora do ciclo de setores.
# camada6: None (só cinco camadas), "mente" (fases, Batman) ou "psique" (cérebro completo, NEX).
PERSONAGENS = {
    HARVEY: {"pasta": "harvey", "chave": "harvey", "nome": "Harvey Specter", "camada6": None,
             "transiciona": False, "instrucoes": "INSTRUCOES_HARVEY.md", "limite": 8000, "nucleo": None,
             "prefixo_bib": "BIB_"},
    BATMAN: {"pasta": "batman", "chave": "batman", "nome": "Batman", "camada6": "mente",
             "transiciona": True, "instrucoes": "INSTRUCOES_BATMAN.md", "limite": 8000, "nucleo": "NUCLEO_BATMAN.md",
             "prefixo_bib": "BIB_B"},
    NEX: {"pasta": "nex", "chave": "nex", "nome": "NEXARION", "camada6": "psique",
          "transiciona": True, "instrucoes": "ADENDO_NEX.md", "limite": 4500, "nucleo": "NUCLEO_NEX.md",
          "prefixo_bib": "BIB_N"},
}
for _perfil in PERSONAGENS.values():
    _perfil["mente"] = _perfil["camada6"] == "mente"
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
        if id_setor in PERSONAGENS:
            perfil = PERSONAGENS[id_setor]
            entrada = self.manifesto.setdefault(perfil["chave"], {})
            entrada.setdefault("nome", perfil["nome"])
            entrada.setdefault("pasta", perfil["pasta"])
            entrada.setdefault("status", "Ativo")
            return entrada
        try:
            return self.manifesto["setores"][id_setor]
        except KeyError:
            raise ErroDeValidacao(f"setor {id_setor} não existe no manifesto") from None

    def pasta_do_setor(self, id_setor: str) -> Path:
        if id_setor in PERSONAGENS:
            return self.raiz / PERSONAGENS[id_setor]["pasta"]
        return self.pasta_setores / self.entrada(id_setor)["pasta"]

    def tem_personagem(self, id_: str) -> bool:
        return id_ in PERSONAGENS and (self.raiz / PERSONAGENS[id_]["pasta"] / CAMADAS[1]).exists()

    def personagens(self) -> list[str]:
        return [p for p in PERSONAGENS if self.tem_personagem(p)]

    @property
    def tem_harvey(self) -> bool:
        return self.tem_personagem(HARVEY)

    def camada6_de(self, id_: str) -> str | None:
        return PERSONAGENS[id_]["camada6"] if id_ in PERSONAGENS else None

    def tem_mente(self, id_: str) -> bool:
        return self.camada6_de(id_) == "mente"

    def tem_psique(self, id_: str) -> bool:
        return self.camada6_de(id_) == "psique"

    def mente_de(self, id_: str) -> tuple[str, Registro, list[Registro]]:
        if not self.tem_mente(id_):
            raise mente_mod.ErroDeMente(f"{id_} não tem Camada 6 do tipo mente")
        return mente_mod.carregar(self.pasta_do_setor(id_))

    def psique_de(self, id_: str) -> tuple[str, dict]:
        if not self.tem_psique(id_):
            raise psique_mod.ErroDePsique(f"{id_} não tem Camada 6 do tipo psique")
        return psique_mod.carregar(self.pasta_do_setor(id_))

    def linha_de_camada6(self, id_: str) -> str:
        if self.tem_mente(id_):
            mente = self.mente_de(id_)[1]
            return f"fase mental {mente.get('fase')} (sanidade {mente.get('sanidade')})"
        if self.tem_psique(id_):
            return "psique: " + psique_mod.linha_de_estado(self.psique_de(id_)[1])
        return ""

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
        for nome in sorted(p.name for p in pasta.iterdir() if p.is_file() and p.suffix == ".md"):
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
        for arquivo, limite in ((ARQUIVO_INSTRUCOES, LIMITE_INSTRUCOES), (ARQUIVO_ADENDO, LIMITE_ADENDO),
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
        for id_p in self.personagens():
            perfil = PERSONAGENS[id_p]
            try:
                personagem = self.setor(id_p)
            except (ErroDeValidacao, ValueError) as erro:
                problemas.append(str(erro))
                continue
            problemas.extend(personagem.validar())
            if not self.diario.versoes(id_p):
                problemas.append(f"{id_p}: sem versão guardada para reversão (use 'versoes guardar {id_p}')")
            caminho = self.raiz / perfil["pasta"] / perfil["instrucoes"]
            if not caminho.exists():
                problemas.append(f"falta {perfil['pasta']}/{perfil['instrucoes']}")
            elif len(caminho.read_text(encoding="utf-8")) > perfil["limite"]:
                problemas.append(f"{perfil['pasta']}/{perfil['instrucoes']} passa de {perfil['limite']} caracteres")
            if perfil["nucleo"] and not (self.raiz / perfil["pasta"] / perfil["nucleo"]).exists():
                problemas.append(f"falta {perfil['pasta']}/{perfil['nucleo']}")
            if perfil["camada6"] == "mente":
                try:
                    _, mente, _ = self.mente_de(id_p)
                except mente_mod.ErroDeMente as erro:
                    problemas.append(f"{id_p}: {erro}")
                else:
                    problemas.extend(f"{id_p}/{m}" for m in mente_mod.validar(mente))
            elif perfil["camada6"] == "psique":
                try:
                    _, estado = self.psique_de(id_p)
                except psique_mod.ErroDePsique as erro:
                    problemas.append(f"{id_p}: {erro}")
                else:
                    problemas.extend(f"{id_p}/{m}" for m in psique_mod.validar(estado))
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
        return self.diario.guardar_versao(id_setor, numero,
                                          sorted(p for p in pasta.iterdir() if p.is_file() and p.suffix == ".md"))

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
        if id_setor not in PERSONAGENS:
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
        if id_setor in PERSONAGENS:
            raise ErroDeValidacao(f"{id_setor} não tem trava mecânica, por decisão de Milan: ele é ele. "
                                  "Só Milan edita o núcleo; a mudança fica no diário via 'versoes guardar'.")
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
        SECOES_MENTE = {"mente", "tempo"}
        SECOES_PSIQUE = {"psique", "significado", "pratica", "tempo"}
        secoes6 = SECOES_MENTE if self.tem_mente(bloco.setor) else SECOES_PSIQUE if self.tem_psique(bloco.setor) else set()
        so_mente = bool(secoes6) and all(secao.tipo in secoes6 for secao in bloco.secoes)
        if entrada["status"] not in ESTADOS_OPERANTES and not so_mente:
            raise ErroDeAutorizacao(
                f"{bloco.setor} está '{entrada['status']}' e não opera; só setores em "
                f"{sorted(ESTADOS_OPERANTES)} recebem aprendizado"
                + (" (eventos da Camada 6 continuam aceitos)" if secoes6 else "")
            )
        usadas = {secao.tipo for secao in bloco.secoes} & {"mente", "tempo", "psique", "significado", "pratica"}
        if usadas - secoes6:
            raise ErroDePatch(f"{bloco.setor} não aceita as seções {sorted(usadas - secoes6)}: "
                              f"Camada 6 = {self.camada6_de(bloco.setor) or 'nenhuma'}")
        trava = entrada.get("trava_camada1")
        setor = self.setor(bloco.setor)
        if trava and trava != setor.hash_camada1():
            raise ErroDeValidacao(
                f"{bloco.setor}: camada 1 difere da trava; corrija antes de aplicar aprendizado"
            )
        relato: list[str] = []
        pendentes: list[Registro] = []
        mente_estado = self.mente_de(bloco.setor) if self.tem_mente(bloco.setor) else None
        fase_antes = mente_estado[1].get("fase") if mente_estado else None
        psique_estado = self.psique_de(bloco.setor) if self.tem_psique(bloco.setor) else None
        alertas_antes = psique_mod.alertas(psique_estado[1]) if psique_estado else []
        for secao in bloco.secoes:
            if mente_estado and secao.tipo in ("mente", "tempo"):
                relato.append(self._aplicar_mente(mente_estado, bloco, secao, hoje))
                continue
            if psique_estado and secao.tipo in ("psique", "significado", "pratica", "tempo"):
                relato.append(self._aplicar_psique(setor, psique_estado[1], bloco, secao, hoje))
                continue
            relato.append(self._aplicar_secao(setor, bloco, secao, hoje, autorizado_por_milan, pendentes))
        problemas = setor.validar()
        if problemas:
            raise ErroDePatch("o bloco deixaria o setor inválido:\n  " + "\n  ".join(problemas))
        versao_anterior = self._antes_de_mudar(bloco.setor)
        setor.salvar()
        if mente_estado:
            mente_mod.salvar(self.pasta_do_setor(bloco.setor), *mente_estado)
        if psique_estado:
            psique_mod.salvar(self.pasta_do_setor(bloco.setor), *psique_estado)
        for dossie in pendentes:
            self._gravar_dossie(dossie)
        self._depois_de_mudar(
            bloco.setor, operacao="aprendizado", diferenca="; ".join(relato),
            motivo=f"bloco de aprendizado de {bloco.data}", responsavel=bloco.emitido_por,
            autorizacao="Milan (--autorizado-por-milan)" if autorizado_por_milan
            else "não exigida: memória do próprio setor", hoje=hoje, versao_anterior=versao_anterior,
        )
        if mente_estado:
            relato.extend(self._consequencias_de_fase(bloco.setor, fase_antes, mente_estado[1], hoje))
        if psique_estado:
            relato.extend(self._consequencias_de_psique(bloco.setor, alertas_antes, psique_estado[1], hoje))
        return relato

    def _aplicar_psique(self, setor: Setor, estado: dict, bloco: BlocoDeAprendizado, secao: Secao,
                        hoje: date) -> str:
        c = secao.campos
        try:
            if secao.tipo == "tempo":
                dias = int(c.get("dias", "0") or 0)
                registro = psique_mod.passar_tempo(estado, dias, relatado_por=bloco.emitido_por, hoje=hoje)
            elif secao.tipo == "psique":
                registro = psique_mod.aplicar_evento(estado, c.get("evento", ""), c.get("intensidade", "normal"),
                                                     c.get("descricao", ""), c.get("pessoa", ""),
                                                     relatado_por=bloco.emitido_por, hoje=hoje)
            elif secao.tipo == "pratica":
                registro = psique_mod.aplicar_pratica(estado, c.get("habilidade", ""), c.get("resultado", ""),
                                                      c.get("dificuldade", "media"), c.get("descricao", ""),
                                                      relatado_por=bloco.emitido_por, hoje=hoje)
            else:
                faltando = [k for k in ("fonte", "conteudo", "significado", "emocao", "valor", "direcao") if not c.get(k)]
                if faltando:
                    raise ErroDePatch(f"'## significado' sem os campos: {', '.join(faltando)}")
                registro = psique_mod.aplicar_significado(estado, c["fonte"], c["conteudo"], c["significado"],
                                                          c["emocao"], c.get("intensidade", "normal"), c["valor"],
                                                          c["direcao"], relatado_por=bloco.emitido_por, hoje=hoje)
                setor.acrescentar("significado", {
                    "fonte": c["fonte"], "conteudo": c["conteudo"], "significado": c["significado"],
                    "emocao": c["emocao"], "intensidade": c.get("intensidade", "normal"), "valor": c["valor"],
                    "direcao": c["direcao"], "data": hoje.isoformat(), "registrado_por": bloco.emitido_por,
                    "status": "vigente",
                })
        except (psique_mod.ErroDePsique, ValueError) as erro:
            raise ErroDePatch(str(erro)) from None
        psique = estado["psique"]
        return (f"{registro.id}: {registro.get('evento')} → {psique.get('emocao_dominante')}, ego {psique.get('ego')}, "
                f"postura {psique.get('postura')}" + ("; agiu por impulso" if registro.get("impulso") == "agiu por impulso" else "")
                + (f"; saúde: {registro.get('saude')}" if registro.get("saude") not in (None, "", "sem mudança") else ""))

    def _consequencias_de_psique(self, id_: str, alertas_antes: list[str], estado: dict, hoje: date) -> list[str]:
        novos = [a for a in psique_mod.alertas(estado) if a not in alertas_antes]
        relato = []
        for problema in novos:
            self.diario.registrar_alteracao(
                componente=id_, operacao="psique", versao_anterior="estado anterior", versao_nova=problema,
                diferenca=psique_mod.linha_de_estado(estado), motivo="psique procedural", responsavel="Núcleo (cálculo)",
                autorizacao="não exigida: consequência do que o personagem viveu", hoje=hoje)
            if problema.startswith("quadro ativo") or "crítica" in problema:
                alerta = self.diario.acrescentar("alertas", {
                    "tipo": "mente", "componente": id_, "problema": f"{id_}: {problema}",
                    "impacto": "desempenho e julgamento afetados; análise com margem",
                    "recomendacao": "Milan registra descanso, convivio, terapia, avaliacao ou medicacao; ATLAS avalia Limitado",
                    "evidencia": f"camada6_psique.md, último evento {estado['psique'].get('ultimo_evento')}",
                    "status": "aberto", "data": hoje.isoformat(), "emitido_por": "Núcleo",
                })
                relato.append(f"{alerta.id}: alerta de psique registrado ({problema})")
        return relato

    def registrar_evento_de_psique(self, id_: str, tipo: str, campos: dict[str, str], relatado_por: str = "Milan",
                                   hoje: date | None = None) -> list[str]:
        """Milan registra evento, significado, prática ou tempo sem passar por bloco."""
        hoje = hoje or date.today()
        preambulo, estado = self.psique_de(id_)
        antes = psique_mod.alertas(estado)
        setor = self.setor(id_)
        bloco = BlocoDeAprendizado(id_, relatado_por, hoje.isoformat())
        relato = [self._aplicar_psique(setor, estado, bloco, Secao(tipo, None, dict(campos)), hoje)]
        versao_anterior = self._antes_de_mudar(id_)
        setor.salvar()
        psique_mod.salvar(self.pasta_do_setor(id_), preambulo, estado)
        self._depois_de_mudar(
            id_, operacao=f"psique_{tipo}", diferenca=relato[0], motivo=campos.get("descricao", "") or NAO_INFORMADO,
            responsavel=relatado_por, autorizacao="não exigida: registro de evento vivido", hoje=hoje,
            versao_anterior=versao_anterior,
        )
        relato.extend(self._consequencias_de_psique(id_, antes, estado, hoje))
        return relato

    def _aplicar_mente(self, mente_estado, bloco: BlocoDeAprendizado, secao: Secao, hoje: date) -> str:
        _, mente, historico = mente_estado
        if secao.tipo == "tempo":
            try:
                dias = int(secao.campos.get("dias", "0"))
            except ValueError:
                raise ErroDePatch("'## tempo' precisa de 'dias: N'") from None
            registro = mente_mod.passar_tempo(mente, historico, dias, relatado_por=bloco.emitido_por, hoje=hoje)
            return f"{registro.id}: {dias} dia(s) → sanidade {mente.get('sanidade')}, fase {mente.get('fase')}"
        evento = secao.campos.get("evento", "")
        try:
            registro = mente_mod.aplicar_evento(
                mente, historico, evento, secao.campos.get("intensidade", "normal"),
                secao.campos.get("descricao", ""), relatado_por=bloco.emitido_por, hoje=hoje)
        except mente_mod.ErroDeMente as erro:
            raise ErroDePatch(str(erro)) from None
        return f"{registro.id}: {evento} → sanidade {mente.get('sanidade')}, fase {mente.get('fase')}"

    def _consequencias_de_fase(self, id_: str, fase_antes: str | None, mente: Registro, hoje: date) -> list[str]:
        """Mudança de fase entra no diário; LIMIAR alerta; CORINGA vai à Quarentena."""
        fase = mente.get("fase")
        relato: list[str] = []
        if fase != fase_antes:
            self.diario.registrar_alteracao(
                componente=id_, operacao="mudanca_de_fase", versao_anterior=f"fase {fase_antes}",
                versao_nova=f"fase {fase} (sanidade {mente.get('sanidade')})",
                diferenca=f"último evento: {mente.get('ultimo_evento')}", motivo="estado mental procedural",
                responsavel="Núcleo (cálculo)", autorizacao="não exigida: consequência do que o personagem viveu",
                hoje=hoje,
            )
            relato.append(f"fase mental: {fase_antes} → {fase}")
        entrada = self.entrada(id_)
        ordem = mente_mod.ORDEM_DAS_FASES
        if fase in ("LIMIAR", "OBSESSIVO") and fase != fase_antes and ordem.index(fase) < ordem.index(fase_antes or "ESTÁVEL"):
            alerta = self.diario.acrescentar("alertas", {
                "tipo": "mente", "componente": id_, "problema": f"{id_} entrou na fase {fase} (sanidade {mente.get('sanidade')})",
                "impacto": "análise pode estar comprometida; risco de decisão ruim",
                "recomendacao": "Milan registra descanso, alfred, terapia ou gordon; ATLAS avalia Limitado",
                "evidencia": f"camada6_mente.md, último evento {mente.get('ultimo_evento')}",
                "status": "aberto", "data": hoje.isoformat(), "emitido_por": "Núcleo",
            })
            relato.append(f"{alerta.id}: alerta de mente registrado para ATLAS e Milan")
        if fase == "CORINGA" and entrada["status"] in ESTADOS_OPERANTES:
            self.transicionar(id_, "quarentena", False, por="NUCLEO",
                              motivo=f"fase CORINGA: sanidade {mente.get('sanidade')}; cedeu à sanidade do Coringa",
                              hoje=hoje)
            alerta = self.diario.acrescentar("alertas", {
                "tipo": "quarentena", "componente": id_, "problema": f"{id_} cedeu à sanidade do Coringa (sanidade {mente.get('sanidade')})",
                "impacto": "bloqueante: nenhuma ordem ou entrega até recuperação",
                "recomendacao": "Milan registra eventos de recuperação (descanso, alfred, terapia, gordon, familia) e reativa quando a fase voltar a SOMBRIO ou melhor",
                "evidencia": "camada6_mente.md", "status": "aberto", "data": hoje.isoformat(), "emitido_por": "Núcleo",
            })
            relato.append(f"{id_} em Quarentena automática ({alerta.id}); só Milan reativa")
        return relato

    def registrar_evento_mental(self, id_: str, evento: str, intensidade: str = "normal", descricao: str = "",
                                relatado_por: str = "Milan", hoje: date | None = None) -> list[str]:
        """Milan (ou o próprio personagem) registra um evento sem passar por bloco."""
        hoje = hoje or date.today()
        mente_estado = self.mente_de(id_)
        fase_antes = mente_estado[1].get("fase")
        _, mente, historico = mente_estado
        if evento == "tempo":
            registro = mente_mod.passar_tempo(mente, historico, int(descricao or "1"), relatado_por, hoje)
        else:
            registro = mente_mod.aplicar_evento(mente, historico, evento, intensidade, descricao, relatado_por, hoje)
        versao_anterior = self._antes_de_mudar(id_)
        mente_mod.salvar(self.pasta_do_setor(id_), *mente_estado)
        self._depois_de_mudar(
            id_, operacao="evento_mental", diferenca=f"{registro.id}: {registro.get('evento')} ({registro.get('deltas')})",
            motivo=descricao or registro.get("descricao", ""), responsavel=relatado_por,
            autorizacao="não exigida: registro de evento vivido", hoje=hoje, versao_anterior=versao_anterior,
        )
        relato = [f"{registro.id}: {registro.get('evento')} → sanidade {mente.get('sanidade')}, fase {mente.get('fase')}"]
        relato.extend(self._consequencias_de_fase(id_, fase_antes, mente, hoje))
        return relato

    def _aplicar_secao(self, setor: Setor, bloco: BlocoDeAprendizado, secao: Secao, hoje: date,
                       autorizado: bool, dossies: list[Registro]) -> str:
        campos = dict(secao.campos)
        data_hoje = hoje.isoformat()
        if secao.tipo in ("fato", "hipotese", "licao", "regra"):
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
            tipo = tipo_do_registro(antigo) or {2: "fato", 3: "hipotese", 4: "licao"}[numero]
            for chave, valor in antigo.campos.items():
                if chave not in campos and chave not in {"status", "superado_por", "superado_em",
                                                          "motivo_superacao", "registrado_em"}:
                    campos.setdefault(chave, valor)
            self._preencher_padroes(tipo, campos, bloco, data_hoje)
            campos["status"] = {"fato": "vigente", "hipotese": "aberta", "licao": "vigente", "regra": "vigente"}[tipo]
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
        elif tipo in ("licao", "regra"):
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
        if origem == setor.id or setor.id in PERSONAGENS:
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
        if id_setor in PERSONAGENS and not PERSONAGENS[id_setor]["transiciona"]:
            raise ErroDeValidacao(f"{id_setor} não é um setor: não muda de estado. Ele é ele.")
        if acao not in TRANSICOES:
            raise ValueError(f"ação desconhecida '{acao}'; use {sorted(TRANSICOES)}")
        if acao == "quarentena":
            if por not in {"Milan", "ATLAS", "NUCLEO"}:
                raise ErroDeAutorizacao("quarentena preventiva só por ATLAS, Milan ou pelo Núcleo (fase CORINGA)")
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
        if destino in ESTADOS_OPERANTES and self.tem_mente(id_setor):
            fase = self.mente_de(id_setor)[1].get("fase")
            if fase in ("CORINGA", "LIMIAR"):
                raise ErroDeValidacao(
                    f"{id_setor} ainda está na fase {fase}; registre eventos de recuperação "
                    "(descanso, alfred, terapia, gordon, familia) até SOMBRIO ou melhor antes de reativar"
                )
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
        for id_p in self.personagens():
            itens = self.setor(id_p).pendencias(hoje)
            if self.tem_mente(id_p):
                fase = self.mente_de(id_p)[1].get("fase")
                status = self.entrada(id_p)["status"]
                if fase in ("OBSESSIVO", "LIMIAR", "CORINGA"):
                    itens.append(f"MENTE: fase {fase}; Milan decide descanso, alfred, terapia, gordon ou familia")
                if status == "Quarentena" and fase in ("SOMBRIO", "ESTÁVEL"):
                    itens.append(f"MENTE: recuperou para {fase}; Milan pode reativar ({id_p})")
            if self.tem_psique(id_p):
                itens.extend(f"PSIQUE: {a}" for a in psique_mod.alertas(self.psique_de(id_p)[1]))
            if itens:
                resultado[id_p] = itens
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
        saida: dict[str, dict[str, object]] = {}
        for id_ in self.personagens() + self.setores_com_camadas():
            saida[id_] = self.setor(id_).metricas()
            if self.tem_mente(id_):
                _, mente, historico = self.mente_de(id_)
                saida[id_]["mente"] = {v: int(mente.get(v)) for v in mente_mod.VARIAVEIS}
                saida[id_]["mente"]["fase"] = mente.get("fase")
                saida[id_]["mente"]["eventos"] = len(historico)
            if self.tem_psique(id_):
                _, estado = self.psique_de(id_)
                ps = estado["psique"]
                saida[id_]["psique"] = {
                    "ego": int(float(ps.get("ego"))), "energia": int(float(ps.get("energia"))),
                    "plasticidade": int(float(ps.get("plasticidade"))), "impulso": int(float(ps.get("impulso"))),
                    "emocao_dominante": ps.get("emocao_dominante"), "postura": ps.get("postura"),
                    "carater": ps.get("carater"), "quadros_ativos": psique_mod._ativos(estado["saude"]),
                    "pessoas": len(estado["pessoas"]), "eventos": len(estado["historico"]),
                    "habilidades": {k: int(v) for k, v in psique_mod.habilidades_de(estado).items()},
                }
        return saida

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
        for origem, nome in ((ARQUIVO_INSTRUCOES, "00_INSTRUCOES_HARVEY.md"),
                             (ARQUIVO_ADENDO, "01_ADENDO_DE_INTEGRACAO.md"),
                             (ARQUIVO_PROTOCOLO, "02_PROTOCOLO_DO_CEREBRO.md")):
            gerados.append(destino / nome)
            shutil.copyfile(self.raiz / origem, destino / nome)
        gerados.append(destino / "03_MANIFESTO.md")
        (destino / "03_MANIFESTO.md").write_text(self._manifesto_md(hoje), encoding="utf-8")
        avisos = self._avisos_de_atlas_md()
        if avisos:
            gerados.append(destino / "04_AVISOS_DE_ATLAS.md")
            (destino / "04_AVISOS_DE_ATLAS.md").write_text(avisos, encoding="utf-8")
        for id_p in self.personagens():
            gerados.append(destino / f"{id_p}_CEREBRO.md")
            (destino / f"{id_p}_CEREBRO.md").write_text(
                self._setor_md(id_p, self.entrada(id_p), self.pasta_do_setor(id_p), hoje), encoding="utf-8")
        if self.tem_harvey:
            for biblioteca in sorted((self.raiz / PASTA_HARVEY / "bibliotecas").glob("BIB_*.md")):
                shutil.copyfile(biblioteca, destino / biblioteca.name)
                gerados.append(destino / biblioteca.name)
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
        for id_p in self.personagens():
            if id_p != HARVEY:
                gerados.extend(self._empacotar_sala_de_personagem(id_p, hoje, avisos))
        return gerados

    def _empacotar_sala_de_personagem(self, id_p: str, hoje: date, avisos: str) -> list[Path]:
        perfil = PERSONAGENS[id_p]
        destino = self.raiz / f"upload_{perfil['pasta']}"
        if destino.exists():
            shutil.rmtree(destino)
        destino.mkdir(parents=True)
        gerados: list[Path] = []
        origem = self.raiz / perfil["pasta"]
        nome_instrucoes = f"00_{perfil['instrucoes']}" if perfil["limite"] >= 8000 else f"00_{perfil['instrucoes'].replace('ADENDO_', 'ADENDO_PARA_O_SEU_')}"
        shutil.copyfile(origem / perfil["instrucoes"], destino / nome_instrucoes)
        gerados.append(destino / nome_instrucoes)
        if perfil["nucleo"]:
            shutil.copyfile(origem / perfil["nucleo"], destino / f"01_{perfil['nucleo']}")
            gerados.append(destino / f"01_{perfil['nucleo']}")
        shutil.copyfile(self.raiz / ARQUIVO_PROTOCOLO, destino / "02_PROTOCOLO_DO_CEREBRO.md")
        gerados.append(destino / "02_PROTOCOLO_DO_CEREBRO.md")
        (destino / "03_MANIFESTO.md").write_text(self._manifesto_md(hoje), encoding="utf-8")
        gerados.append(destino / "03_MANIFESTO.md")
        if avisos:
            (destino / "04_AVISOS_DE_ATLAS.md").write_text(avisos, encoding="utf-8")
            gerados.append(destino / "04_AVISOS_DE_ATLAS.md")
        (destino / f"{id_p}_CEREBRO.md").write_text(
            self._setor_md(id_p, self.entrada(id_p), origem, hoje), encoding="utf-8")
        gerados.append(destino / f"{id_p}_CEREBRO.md")
        for biblioteca in sorted((origem / "bibliotecas").glob(f"{perfil['prefixo_bib']}*.md")):
            shutil.copyfile(biblioteca, destino / biblioteca.name)
            gerados.append(destino / biblioteca.name)
        for id_setor in self.setores_com_camadas():
            entrada = self.entrada(id_setor)
            nome = f"{id_setor}_{slug(entrada['nome']).upper()}.md"
            (destino / nome).write_text(self._setor_md(id_setor, entrada, self.pasta_do_setor(id_setor), hoje),
                                        encoding="utf-8")
            gerados.append(destino / nome)
        if self.dossies():
            shutil.copyfile(self.pasta_dossies / "dossies.md", destino / "90_DOSSIES.md")
            gerados.append(destino / "90_DOSSIES.md")
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
        quarentenas = [s for s in self.personagens() + self.setores()
                       if self.entrada(s)["status"] in {"Quarentena", "Limitado"}]
        fases = []
        for id_p in self.personagens():
            if self.tem_mente(id_p):
                mente = self.mente_de(id_p)[1]
                if mente.get("fase") != "ESTÁVEL":
                    fases.append(f"- {id_p} está na fase mental **{mente.get('fase')}** (sanidade {mente.get('sanidade')}): "
                                 "leia as análises dele com essa margem.")
            if self.tem_psique(id_p):
                problemas = psique_mod.alertas(self.psique_de(id_p)[1])
                if problemas:
                    fases.append(f"- {id_p}: {'; '.join(problemas)}. Leia as análises dele com essa margem.")
        if not (alertas or recomendacoes or quarentenas or fases):
            return ""
        linhas = ["# Avisos de ATLAS para Harvey e os setores", "",
                  "ATLAS governa a estrutura; estes avisos são dados a considerar, não ordens acima de Milan.", ""]
        linhas.extend(fases)
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
        for id_p in self.personagens():
            h = self.setor(id_p).metricas()
            entrada = self.entrada(id_p)
            linhas += ["", f"## {entrada['nome']} ({id_p})", "",
                       f"Status **{entrada['status']}**, cérebro próprio ({id_p}_CEREBRO.md), versão v{self.versao_de(id_p):03d}: "
                       f"{h['fatos_vigentes']} fatos, {sum(h['hipoteses'].values())} hipóteses, "
                       f"{sum(h['licoes_vigentes'].values())} lições, {h['regras_vigentes']} regras próprias vigentes. "
                       "Núcleo sem trava mecânica, por decisão de Milan."]
            if self.tem_mente(id_p):
                mente = self.mente_de(id_p)[1]
                linhas.append(f"Fase mental: **{mente.get('fase')}** (sanidade {mente.get('sanidade')}, "
                              f"exaustão {mente.get('exaustao')}, isolamento {mente.get('isolamento')}, "
                              f"exposição ao caos {mente.get('exposicao_ao_caos')}).")
            if self.tem_psique(id_p):
                linhas.append("Psique hoje: " + psique_mod.linha_de_estado(self.psique_de(id_p)[1]) + ".")
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
        if id_setor in PERSONAGENS:
            trava = f"A Camada 1 é a identidade de {PERSONAGENS[id_setor]['nome']}; sem trava mecânica, por decisão de Milan."
            titulo1 = "## Camada 1 — Núcleo de identidade"
        else:
            trava = f"A Camada 1 é travada (hash {setor.hash_camada1()[:12]})."
            titulo1 = "## Camada 1 — Núcleo travado"
        partes = [f"<!-- {id_setor} · status: {entrada['status']} · versão v{self.versao_de(id_setor):03d} · "
                  f"hash camada 1: {setor.hash_camada1()[:12]} · gerado em {hoje.isoformat()} -->", "",
                  "# " + setor.nome, "", f"Status: **{entrada['status']}**.{restricao} Este arquivo é o cérebro "
                  f"completo. {trava}", "",
                  "---", "", titulo1, "",
                  _rebaixar_titulos(_sem_titulo(setor.camada1))]
        for numero in (2, 3, 4, 5):
            texto = render_registros(_sem_titulo(setor.preambulos[numero]), setor.registros[numero])
            partes += ["", "---", "", f"## {titulos[numero]}", "", _rebaixar_titulos(texto)]
        if self.tem_mente(id_setor):
            _, mente, historico = self.mente_de(id_setor)
            partes += ["", "---", "", "## Camada 6 — Mente", "", mente_mod.resumo(mente, historico)]
        if self.tem_psique(id_setor):
            _, estado = self.psique_de(id_setor)
            partes += ["", "---", "", "## Camada 6 — Psique (como NEX está hoje)", "", psique_mod.resumo(estado)]
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
