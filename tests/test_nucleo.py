import io
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path

from nucleo import (
    ErroDeAutorizacao, ErroDeFormato, ErroDeIsolamento, ErroDePatch, ErroDeValidacao, Projeto,
    parse_bloco, parse_registros, render_registros,
)
from nucleo import mente as mente_mod
from nucleo import psique as psique_mod
from nucleo.__main__ import main
from nucleo.atlas import empacotar_atlas, integridade, registro_global
from nucleo.patch import extrair_blocos, parse_bloco_atlas
from nucleo.projeto import LIMITE_ADENDO, LIMITE_INSTRUCOES, SECOES_DA_CARTA
from nucleo.setor import CAMADAS

RAIZ = Path(__file__).resolve().parent.parent
GPT_PROJETO = RAIZ / "gpt_projeto"
HOJE = date(2026, 9, 4)


def bloco(setor="S01", emitido_por="RAIO-X", corpo=""):
    return parse_bloco(f"setor: {setor}\nemitido_por: {emitido_por}\ndata: 2026-09-04\n\n{corpo}")


FATO = "## fato\n- conteudo: Milan trabalhou 2 anos numa clínica.\n- fonte: Milan\n- confianca: alta\n"
HIPOTESE = (
    "## hipotese\n- conteudo: Agendamento remoto para clínicas.\n- evidencia_favoravel: rotina comprovada\n"
    "- evidencia_contraria: nenhuma clínica sondada\n- teste: 5 mensagens\n- revisao: 2026-09-11\n"
    "- abandono: zero respostas\n- confianca: media\n"
)
ESTADO = (
    "## estado\n- tarefa_ativa: Calcular prazo\n- prazo: 2026-09-06\n- proxima_acao: Perguntar gasto\n"
    "- bloqueios: nenhum\n- autorizacoes_pendentes: nenhuma\n"
)
def _corpo_da_carta(secao: str) -> str:
    if secao == "Nome":
        return "Custos Fixos"
    if secao == "Responsável pela criação":
        return "Harvey"
    if secao == "Agentes necessários":
        return "### PODA — corte\nPensa por cortes."
    return f"texto de {secao}"


CARTA = "\n".join(f"## {secao}\n{_corpo_da_carta(secao)}\n" for secao in SECOES_DA_CARTA)
BLOCO_ATLAS = """```atlas
emitido_por: ATLAS
data: 2026-09-05

## status
- status: ATENÇÃO
- observado: S02 em piloto
- problema: consumo não medido
- impacto: créditos
- recomendacao: registrar custos
- custo: não medido
- autorizacao: nenhuma
- proximo_movimento: registrar o primeiro custo

## evento_recebido E-002
- parecer: recomenda ativação

## alerta
- componente: S02
- problema: teste sem critério
- impacto: qualidade
- recomendacao: definir critério
- evidencia: carta

## recomendacao
- conteudo: Registrar consumo semanal
- impacto: medio
- urgencia: media
- confianca: alta
- esforco: baixo
- custo: baixo
- risco: nenhum
- reversibilidade: total

## quarentena S02
- motivo: tentou escrever no S01
```
"""


class ProjetoTemporario(unittest.TestCase):
    def setUp(self) -> None:
        mente_mod.semear(1234)
        psique_mod.semear(1234)
        self.tmp = Path(tempfile.mkdtemp())
        self.raiz = self.tmp / "gp"
        shutil.copytree(GPT_PROJETO, self.raiz, ignore=shutil.ignore_patterns("upload_harvey", "upload_setores", "upload_atlas", "upload_batman", "upload_nex", "upload_house", "upload_lobo", "upload_mesas"))
        self.projeto = Projeto.abrir(self.raiz)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def aplicar(self, corpo, setor="S01", autorizado=False, emitido_por=None):
        if emitido_por is None:
            emitido_por = setor if setor in ("HARVEY", "BATMAN", "NEX", "HOUSE", "LOBO") else "RAIO-X"
        return self.projeto.aplicar(bloco(setor, emitido_por, corpo), autorizado_por_milan=autorizado, hoje=HOJE)

    def recarregar(self) -> Projeto:
        self.projeto = Projeto.abrir(self.raiz)
        return self.projeto


class RegistrosTests(unittest.TestCase):
    def test_parse_e_render_preservam_preambulo_e_multilinha(self) -> None:
        texto = "# Título\n\nIntro.\n\n## F-001\n- conteudo: linha um\n  linha dois\n- fonte: x\n"
        preambulo, registros = parse_registros(texto)
        self.assertEqual(preambulo, "# Título\n\nIntro.")
        self.assertEqual(registros[0].get("conteudo"), "linha um\nlinha dois")
        self.assertEqual(render_registros(preambulo, registros), texto)

    def test_campo_repetido_e_linha_solta_sao_erros(self) -> None:
        with self.assertRaises(ErroDeFormato):
            parse_registros("## F-001\n- a: 1\n- a: 2\n")
        with self.assertRaises(ErroDeFormato):
            parse_registros("## F-001\nlinha sem traço\n")


class PatchTests(unittest.TestCase):
    def test_extrai_blocos_de_uma_resposta_inteira(self) -> None:
        resposta = "Harvey: ok.\n\n```aprendizado\nsetor: S01\nemitido_por: X\ndata: 2026-09-04\n\n" + FATO + "```\nfim"
        blocos = extrair_blocos(resposta)
        self.assertEqual(len(blocos), 1)
        self.assertEqual(blocos[0][0], "aprendizado")
        self.assertEqual(parse_bloco(blocos[0][1]).secoes[0].tipo, "fato")
        self.assertEqual(extrair_blocos("emitido_por: ATLAS\ndata: 2026-09-05\n\n## status\n- status: ÍNTEGRO\n")[0][0], "atlas")

    def test_cabecalho_obrigatorio_e_secao_desconhecida(self) -> None:
        with self.assertRaises(ErroDePatch):
            parse_bloco("setor: S01\n\n" + FATO)
        with self.assertRaises(ErroDePatch):
            bloco(corpo="## camada1\n- missao: nova\n")
        with self.assertRaises(ErroDePatch):
            bloco(corpo="## supera\n- motivo: sem alvo\n")


class ProjetoFundadorTests(ProjetoTemporario):
    def test_projeto_do_repositorio_e_valido(self) -> None:
        self.assertEqual(self.projeto.validar(), [])

    def test_instrucoes_cabem_no_campo_do_projeto(self) -> None:
        texto = (GPT_PROJETO / "harvey" / "ADENDO_HARVEY.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(texto), LIMITE_ADENDO)
        self.assertIn("abrir a sala do S01 e colar a ordem", texto)
        self.assertIn("não muda quem Harvey é", texto)
        origem = (GPT_PROJETO / "harvey" / "NUCLEO_HARVEY.md").read_text(encoding="utf-8")
        self.assertIn("Sou Harvey Reginald Specter", origem)
        self.assertIn("Natureza: identidade travada", origem)

    def test_estado_inicial_aponta_para_a_pergunta_de_inicializacao(self) -> None:
        estado = self.projeto.setor("S01").estado
        self.assertIn("No seu último emprego", estado.get("proxima_acao"))
        self.assertEqual(self.projeto.entrada("S01")["status"], "Ativo")

    def test_amazon_e_hipotese_e_nao_fato(self) -> None:
        setor = self.projeto.setor("S01")
        self.assertTrue(any("Amazon" in h.get("conteudo") for h in setor.hipoteses))
        for fato in setor.fatos:
            if "Amazon" in fato.get("conteudo"):
                self.assertNotIn("fonte de renda", fato.get("conteudo"))


class AprendizadoTests(ProjetoTemporario):
    def test_fato_hipotese_licao_e_estado(self) -> None:
        relato = self.aplicar(FATO + HIPOTESE + "## licao\n- conteudo: perguntar rotina\n- origem: evidencia\n" + ESTADO)
        self.assertEqual(len(relato), 4)
        setor = self.recarregar().setor("S01")
        novo = setor.fatos[-1]
        self.assertEqual(novo.id, "F-007")
        self.assertEqual(novo.get("setor_origem"), "S01")
        self.assertEqual(novo.get("registrado_por"), "RAIO-X")
        self.assertEqual(setor.hipoteses[-1].get("status"), "aberta")
        self.assertEqual(setor.licoes[-1].id, "L-002")
        self.assertEqual(setor.estado.get("tarefa_ativa"), "Calcular prazo")
        self.assertEqual(self.projeto.validar(), [])

    def test_correcao_preserva_historico(self) -> None:
        self.aplicar(
            "## correcao\n- substitui: F-004\n- motivo: Milan corrigiu\n"
            "- conteudo: Conta de comprador, não de vendedor.\n- fonte: Milan\n"
            "## licao\n- conteudo: não presumir tipo de conta\n- origem: correcao_milan\n"
        )
        setor = self.recarregar().setor("S01")
        antigo = setor.buscar("F-004")[1]
        novo = setor.fatos[-1]
        self.assertEqual(antigo.get("status"), "superado")
        self.assertEqual(antigo.get("superado_por"), novo.id)
        self.assertIn("Amazon", antigo.get("conteudo"))
        self.assertEqual(novo.get("corrige"), "F-004")
        self.assertEqual(novo.get("status"), "vigente")
        self.assertEqual(novo.get("confianca"), "alta")
        self.assertEqual(setor.metricas()["fatos_superados"], 1)
        with self.assertRaises(ErroDeValidacao):
            self.aplicar("## supera F-004\n- motivo: de novo\n")

    def test_resultado_encerra_hipotese_e_calibra(self) -> None:
        self.aplicar("## resultado H-001\n- status: refutada\n- resultado: sem capital\n")
        setor = self.recarregar().setor("S01")
        self.assertEqual(setor.buscar("H-001")[1].get("status"), "refutada")
        self.assertEqual(setor.metricas()["calibracao"]["baixa"]["refutadas"], 1)
        with self.assertRaises(ErroDePatch):
            self.aplicar("## resultado H-001\n- status: confirmada\n- resultado: x\n")

    def test_hipotese_sem_campos_obrigatorios_e_recusada(self) -> None:
        with self.assertRaises(ErroDePatch):
            self.aplicar("## hipotese\n- conteudo: só isso\n")
        self.assertEqual(len(self.recarregar().setor("S01").hipoteses), 1)

    def test_bloco_com_erro_nao_grava_nada(self) -> None:
        with self.assertRaises(ErroDePatch):
            self.aplicar(FATO + "## hipotese\n- conteudo: incompleta\n")
        self.assertEqual(len(self.recarregar().setor("S01").fatos), 6)

    def test_ids_do_bloco_sao_ignorados_e_atribuidos_pelo_nucleo(self) -> None:
        self.aplicar(FATO)
        self.aplicar(FATO)
        ids = [f.id for f in self.recarregar().setor("S01").fatos]
        self.assertEqual(ids[-2:], ["F-007", "F-008"])


class IsolamentoTests(ProjetoTemporario):
    def test_fato_de_outro_setor_sem_dossie_e_recusado(self) -> None:
        with self.assertRaises(ErroDeIsolamento):
            self.aplicar("## fato\n- conteudo: x\n- fonte: y\n- confianca: alta\n- setor_origem: S02\n")

    def test_correcao_de_registro_de_outro_setor_e_recusada(self) -> None:
        self.projeto.propor_setor("S02", CARTA)
        for acao in ("aprovar", "piloto"):
            self.projeto.transicionar("S02", acao, True)
        with self.assertRaises(ErroDeIsolamento):
            self.aplicar("## correcao\n- substitui: F-001\n- motivo: x\n- conteudo: y\n", setor="S02")
        self.assertEqual(self.recarregar().setor("S01").buscar("F-001")[1].get("status"), "vigente")

    def test_setor_inexistente_ou_nao_operante_nao_recebe_aprendizado(self) -> None:
        with self.assertRaises(ErroDeValidacao):
            self.aplicar(FATO, setor="S09")
        self.projeto.propor_setor("S02", CARTA)
        with self.assertRaises(ErroDeAutorizacao):
            self.aplicar(FATO, setor="S02")

    def test_camada1_alterada_sem_autorizacao_bloqueia_tudo(self) -> None:
        caminho = self.raiz / "setores" / "S01_rota_de_renda" / CAMADAS[1]
        caminho.write_text(caminho.read_text(encoding="utf-8") + "\nRegra nova.\n", encoding="utf-8")
        problemas = self.projeto.validar()
        self.assertTrue(any("camada 1 foi alterada" in p for p in problemas))
        with self.assertRaises(ErroDeValidacao):
            self.aplicar(FATO)
        with self.assertRaises(ErroDeAutorizacao):
            self.projeto.travar("S01", False)
        self.projeto.travar("S01", True)
        self.assertEqual(self.projeto.validar(), [])


class DossieTests(ProjetoTemporario):
    DOSSIE = (
        "## dossie\n- para: S02\n- fato: prazo de 6 semanas\n- fonte: CAIXA\n- confianca: media\n"
        "- restricao: só priorizar\n- pergunta: custo fixo redutível?\n- sensivel: {sensivel}\n"
    )
    RECEBIDO = (
        "## fato\n- conteudo: prazo de 6 semanas\n- fonte: dossiê D-001\n- confianca: media\n"
        "- setor_origem: S01\n- dossie: D-001\n"
    )

    def preparar_s02(self) -> None:
        self.projeto.propor_setor("S02", CARTA)
        for acao in ("aprovar", "piloto", "ativar"):
            self.projeto.transicionar("S02", acao, True)

    def test_dossie_sensivel_espera_milan(self) -> None:
        self.preparar_s02()
        self.aplicar(self.DOSSIE.format(sensivel="sim"))
        self.assertEqual(self.projeto.dossie("D-001").get("status"), "pendente")
        self.assertIn("dossies", self.projeto.pendencias(HOJE))
        with self.assertRaises(ErroDeIsolamento):
            self.aplicar(self.RECEBIDO, setor="S02")
        with self.assertRaises(ErroDeAutorizacao):
            self.projeto.decidir_dossie("D-001", "autorizar", False)
        self.projeto.decidir_dossie("D-001", "autorizar", True)
        self.aplicar(self.RECEBIDO, setor="S02")
        self.assertEqual(self.projeto.dossie("D-001").get("status"), "entregue")
        fato = self.recarregar().setor("S02").fatos[-1]
        self.assertEqual(fato.get("setor_origem"), "S01")
        self.assertEqual(self.projeto.validar(), [])

    def test_dossie_comum_e_autorizado_e_recusado_nao_entrega(self) -> None:
        self.preparar_s02()
        self.aplicar(self.DOSSIE.format(sensivel="nao"))
        self.assertEqual(self.projeto.dossie("D-001").get("status"), "autorizado")
        self.aplicar(self.DOSSIE.format(sensivel="sim"))
        self.projeto.decidir_dossie("D-002", "recusar", True)
        with self.assertRaises(ErroDeIsolamento):
            self.aplicar(self.RECEBIDO.replace("D-001", "D-002"), setor="S02")

    def test_dossie_para_setor_inexistente_ou_para_si(self) -> None:
        with self.assertRaises(ErroDeIsolamento):
            self.aplicar(self.DOSSIE.format(sensivel="nao"))
        with self.assertRaises(ErroDePatch):
            self.aplicar(self.DOSSIE.format(sensivel="nao").replace("para: S02", "para: S01"))


class CicloDeVidaTests(ProjetoTemporario):
    def test_carta_incompleta_e_recusada(self) -> None:
        with self.assertRaises(ErroDeValidacao):
            self.projeto.propor_setor("S02", "## Nome\nX\n")
        with self.assertRaises(ErroDeValidacao):
            self.projeto.propor_setor("Setor2", CARTA)

    def test_transicoes_exigem_milan_e_seguem_a_ordem(self) -> None:
        pasta = self.projeto.propor_setor("S02", CARTA)
        self.assertTrue((pasta / "carta.md").exists())
        self.assertEqual(self.projeto.entrada("S02")["status"], "Proposto")
        with self.assertRaises(ErroDeAutorizacao):
            self.projeto.transicionar("S02", "aprovar", False)
        with self.assertRaises(ErroDeValidacao):
            self.projeto.transicionar("S02", "ativar", True)
        self.projeto.transicionar("S02", "aprovar", True)
        for nome in CAMADAS.values():
            self.assertTrue((pasta / nome).exists(), nome)
        self.assertTrue(self.projeto.entrada("S02")["trava_camada1"])
        self.assertEqual(self.projeto.validar(), [])
        self.projeto.transicionar("S02", "piloto", True)
        self.projeto.transicionar("S02", "ativar", True)
        self.projeto.transicionar("S02", "pausar", True)
        with self.assertRaises(ErroDeAutorizacao):
            self.aplicar(FATO, setor="S02")
        self.projeto.transicionar("S02", "reativar", True)
        self.projeto.transicionar("S02", "encerrar", True)
        self.assertEqual(self.projeto.entrada("S02")["status"], "Encerrado")
        self.assertEqual(len(self.projeto.entrada("S02")["historico"]), 6)


class PendenciasEPacoteTests(ProjetoTemporario):
    def test_pendencias_vencidas_aparecem(self) -> None:
        self.assertNotIn("S01", self.projeto.pendencias(HOJE))  # House já nasce com pendência de psique
        depois = date(2026, 9, 20)
        itens = self.projeto.pendencias(depois)["S01"]
        self.assertTrue(any(i.startswith("F-003") for i in itens))
        self.assertTrue(any(i.startswith("H-001") for i in itens))
        self.assertTrue(any(i.startswith("ESTADO: prazo") for i in itens))

    def test_empacotar_gera_arquivos_para_o_projeto(self) -> None:
        gerados = self.projeto.empacotar(hoje=HOJE)
        nomes = [str(g.relative_to(self.raiz)) for g in gerados]
        bibliotecas = [f"upload_harvey/{b.name}" for b in sorted((GPT_PROJETO / "harvey" / "bibliotecas").glob("BIB_*.md"))]
        self.assertEqual(len(bibliotecas), 10)
        esperado = [
            "upload_harvey/00_ADENDO_PARA_O_SEU_HARVEY.md", "upload_harvey/01_INSTRUCOES_ORIGINAIS_DO_SEU_HARVEY.md",
            "upload_harvey/01_NUCLEO_HARVEY.md", "upload_harvey/02_PROTOCOLO_DO_CEREBRO.md", "upload_harvey/03_MANIFESTO.md",
            "upload_harvey/HARVEY_CEREBRO.md", "upload_harvey/BATMAN_CEREBRO.md", "upload_harvey/NEX_CEREBRO.md",
            "upload_harvey/HOUSE_CEREBRO.md", "upload_harvey/LOBO_CEREBRO.md", *bibliotecas,
            "upload_harvey/S01_ROTA_DE_RENDA.md",
            "upload_setores/S01/00_INSTRUCOES_S01.md", "upload_setores/S01/01_PROTOCOLO_DO_CEREBRO.md",
            "upload_setores/S01/02_MANIFESTO.md", "upload_setores/S01/S01_ROTA_DE_RENDA.md"]
        nomes_sem_avisos = [n for n in nomes if "AVISOS_DE_ATLAS" not in n]
        self.assertEqual(nomes_sem_avisos[:len(esperado)], esperado)
        self.assertIn("upload_batman/00_INSTRUCOES_BATMAN.md", nomes)
        self.assertIn("upload_batman/01_NUCLEO_BATMAN.md", nomes)
        self.assertIn("upload_batman/BATMAN_CEREBRO.md", nomes)
        self.assertEqual(sum(1 for n in nomes if n.startswith("upload_batman/BIB_B")), 10)
        self.assertIn("upload_nex/00_ADENDO_PARA_O_SEU_NEX.md", nomes)
        self.assertIn("upload_nex/01_NUCLEO_NEX.md", nomes)
        self.assertIn("upload_nex/NEX_CEREBRO.md", nomes)
        self.assertEqual(sum(1 for n in nomes if n.startswith("upload_nex/BIB_N")), 3)
        self.assertIn("upload_house/00_ADENDO_PARA_O_SEU_HOUSE.md", nomes)
        self.assertEqual(sum(1 for n in nomes if n.startswith("upload_house/BIB_H")), 6)
        self.assertFalse(any("testes" in n for n in nomes))
        self.assertIn("upload_lobo/00_ADENDO_PARA_O_SEU_LOBO.md", nomes)
        self.assertEqual(sum(1 for n in nomes if n.startswith("upload_lobo/BIB_L")), 6)
        setor_md = (self.raiz / "upload_harvey" / "S01_ROTA_DE_RENDA.md").read_text(encoding="utf-8")
        for trecho in ("## Camada 1", "### Missão", "### F-001", "### H-001", "### L-001", "### ESTADO",
                       "hash camada 1"):
            self.assertIn(trecho, setor_md)
        manifesto = (self.raiz / "upload_harvey" / "03_MANIFESTO.md").read_text(encoding="utf-8")
        self.assertIn("| S01 | Rota de Renda | Ativo | v001 |", manifesto)
        self.assertIn("### HOUSE", manifesto)  # House nasce com pendência de psique

    def test_empacotar_recusa_projeto_invalido(self) -> None:
        caminho = self.raiz / "setores" / "S01_rota_de_renda" / CAMADAS[1]
        caminho.write_text(caminho.read_text(encoding="utf-8") + "x\n", encoding="utf-8")
        with self.assertRaises(ErroDeValidacao):
            self.projeto.empacotar(hoje=HOJE)

    def test_sala_do_setor_e_o_setor_e_nao_harvey(self) -> None:
        self.projeto.empacotar(hoje=HOJE)
        instrucoes = (self.raiz / "upload_setores" / "S01" / "00_INSTRUCOES_S01.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(instrucoes), LIMITE_INSTRUCOES)
        self.assertIn("Você é o Setor S01 — Rota de Renda", instrucoes)
        self.assertIn("Você não é Harvey e não é ATLAS", instrucoes)
        self.assertIn("**Harvey**", instrucoes)
        self.assertIn("**ATLAS**", instrucoes)
        for agente in ("RAIO-X", "RADAR", "CAIXA", "OFICINA", "CONTRADITÓRIO"):
            self.assertIn(agente, instrucoes)
        self.assertIn("No seu último emprego, o que você fazia no dia a dia?", instrucoes)
        self.assertIn("S01_ROTA_DE_RENDA.md", instrucoes)
        self.assertIn("```entrega", instrucoes)
        self.assertNotIn("{", instrucoes.replace("{ID}", "").replace("{NOME}", ""))
        harvey = (self.raiz / "upload_harvey" / "01_INSTRUCOES_ORIGINAIS_DO_SEU_HARVEY.md").read_text(encoding="utf-8")
        self.assertIn("Você é Harvey Specter", harvey)
        adendo = (self.raiz / "upload_harvey" / "00_ADENDO_PARA_O_SEU_HARVEY.md").read_text(encoding="utf-8")
        self.assertIn("```ordem", adendo)
        self.assertIn("HARVEY_CEREBRO.md", adendo)
        self.assertNotIn("Você é o Setor", adendo)

    def test_sala_do_setor_recebe_so_os_proprios_dossies(self) -> None:
        self.projeto.propor_setor("S02", CARTA, hoje=HOJE)
        for acao in ("aprovar", "piloto", "ativar"):
            self.projeto.transicionar("S02", acao, True, hoje=HOJE)
        self.projeto.propor_setor("S03", CARTA.replace("Custos Fixos", "Terceiro"), hoje=HOJE)
        for acao in ("aprovar", "piloto"):
            self.projeto.transicionar("S03", acao, True, hoje=HOJE)
        self.aplicar("## dossie\n- para: S02\n- fato: x\n- fonte: y\n- confianca: alta\n- restricao: r\n- pergunta: p\n")
        self.projeto.empacotar(hoje=HOJE)
        self.assertTrue((self.raiz / "upload_setores" / "S02" / "90_DOSSIES.md").exists())
        self.assertTrue((self.raiz / "upload_setores" / "S01" / "90_DOSSIES.md").exists())
        self.assertFalse((self.raiz / "upload_setores" / "S03" / "90_DOSSIES.md").exists())
        self.assertTrue((self.raiz / "upload_setores" / "S03" / "00_INSTRUCOES_S03.md").exists())

    def test_pacote_versionado_esta_sincronizado_com_as_camadas(self) -> None:
        """Os pacotes commitados devem refletir as camadas atuais (rode `nucleo empacotar`)."""
        self.projeto.empacotar(hoje=HOJE)
        for pasta in ("upload_harvey", "upload_setores", "upload_batman", "upload_nex", "upload_house", "upload_lobo"):
            for caminho in sorted((self.raiz / pasta).rglob("*.md")):
                relativo = caminho.relative_to(self.raiz)
                atual = GPT_PROJETO / relativo
                self.assertTrue(atual.exists(), f"falta gpt_projeto/{relativo}: rode nucleo empacotar")
                esperado = [l for l in caminho.read_text(encoding="utf-8").splitlines() if "gerado em" not in l.lower()]
                existente = [l for l in atual.read_text(encoding="utf-8").splitlines() if "gerado em" not in l.lower()]
                self.assertEqual(existente, esperado, f"gpt_projeto/{relativo} desatualizado: rode nucleo empacotar")


class DiarioEVersoesTests(ProjetoTemporario):
    def test_toda_mudanca_entra_no_diario_com_versoes(self) -> None:
        self.aplicar(FATO)
        alteracoes = self.projeto.diario.ler("alteracoes")
        ultima = alteracoes[-1]
        self.assertEqual(ultima.get("componente"), "S01")
        self.assertEqual(ultima.get("operacao"), "aprendizado")
        self.assertTrue(ultima.get("versao_anterior").startswith("v001"))
        self.assertTrue(ultima.get("versao_proposta").startswith("v002"))
        self.assertEqual(ultima.get("responsavel"), "RAIO-X")
        self.assertIn("reverter S01 v001", ultima.get("plano_de_reversao"))
        self.assertEqual([v.name for v in self.projeto.diario.versoes("S01")], ["v001", "v002"])

    def test_reverter_restaura_baseline_e_registra(self) -> None:
        self.aplicar(FATO)
        with self.assertRaises(ErroDeAutorizacao):
            self.projeto.reverter("S01", "v001", False, hoje=HOJE)
        self.projeto.reverter("S01", "v001", True, motivo="teste", hoje=HOJE)
        setor = self.recarregar().setor("S01")
        self.assertEqual(len(setor.fatos), 6)
        self.assertEqual(self.projeto.versao_de("S01"), 3)
        self.assertEqual(self.projeto.diario.ler("alteracoes")[-1].get("operacao"), "reversao")
        self.assertEqual(self.projeto.validar(), [])

    def test_travar_registra_agente_novo_como_evento(self) -> None:
        caminho = self.raiz / "setores" / "S01_rota_de_renda" / CAMADAS[1]
        caminho.write_text(caminho.read_text(encoding="utf-8") + "\n### VIGIA — alerta\nPensa por sinais.\n",
                           encoding="utf-8")
        self.projeto.travar("S01", True, motivo="novo agente", hoje=HOJE)
        evento = self.projeto.diario.ler("eventos")[-1]
        self.assertEqual(evento.get("evento"), "MUDANCA_DE_NUCLEO")
        self.assertIn("VIGIA", evento.get("diferenca"))
        self.assertEqual(evento.get("status"), "pendente_para_atlas")
        self.assertEqual(self.projeto.validar(), [])

    def test_nucleo_de_atlas_e_travado(self) -> None:
        caminho = self.raiz / "atlas" / "NUCLEO_ATLAS.md"
        caminho.write_text(caminho.read_text(encoding="utf-8") + "\nregra nova\n", encoding="utf-8")
        self.assertTrue(any("ATLAS: núcleo foi alterado" in p for p in self.projeto.validar()))
        self.projeto.travar("ATLAS", True, hoje=HOJE)
        self.assertEqual(self.projeto.validar(), [])
        self.assertEqual(self.projeto.manifesto["atlas"]["versao"], 2)


class AtlasTests(ProjetoTemporario):
    def preparar_s02(self) -> None:
        self.projeto.propor_setor("S02", CARTA, hoje=HOJE)
        self.projeto.transicionar("S02", "aprovar", True, hoje=HOJE)
        self.projeto.transicionar("S02", "piloto", True, hoje=HOJE)

    def test_propor_gera_evento_novo_setor_completo(self) -> None:
        self.projeto.propor_setor("S02", CARTA, hoje=HOJE)
        evento = self.projeto.diario.ler("eventos")[-1]
        self.assertEqual(evento.get("evento"), "NOVO_SETOR")
        for campo in ("missao", "problema_que_resolve", "escopo_permitido", "atividades_proibidas",
                      "cerebro_ou_metodo", "agentes_internos", "prompt_principal_e_versao",
                      "ferramentas_solicitadas", "dados_de_entrada", "entregaveis", "metricas",
                      "dependencias", "riscos", "orcamento_ou_limite", "condicao_de_parada",
                      "responsavel_pela_criacao"):
            self.assertTrue(evento.get(campo), campo)
        self.assertEqual(evento.get("autorizacao_de_milan"), "pendente")
        self.projeto.transicionar("S02", "aprovar", True, hoje=HOJE)
        self.assertIn("concedida", self.projeto.diario.ler("eventos")[-1].get("autorizacao_de_milan"))

    def test_registro_global_lista_todos_os_componentes(self) -> None:
        self.preparar_s02()
        ids = [r.id for r in registro_global(self.projeto, HOJE)]
        harvey = next(r for r in registro_global(self.projeto, HOJE) if r.id == "HARVEY")
        self.assertIn("sem trava mecânica", harvey.get("versao_atual"))
        self.assertIn("regras próprias", harvey.get("dados_mantidos"))
        for esperado in ("ATLAS", "HARVEY", "PROMPT-BASE", "PROMPT-ATLAS", "NUCLEO", "S01", "S01/RAIO-X",
                         "S01/CONTRADITÓRIO", "S01/MEMORIA", "S02", "S02/PODA", "MANIFESTO", "DOSSIES", "DIARIO"):
            self.assertIn(esperado, ids)
        registro = next(r for r in registro_global(self.projeto, HOJE) if r.id == "S01")
        for campo in ("nome", "tipo", "missao", "responsavel", "autoridade", "limites", "versao_atual",
                      "estado_operacional", "dependencias", "dados_mantidos", "localizacao",
                      "custo_operacional", "riscos_conhecidos", "ultima_alteracao", "autorizacao_da_alteracao"):
            self.assertTrue(registro.get(campo), campo)
        self.assertEqual(registro.get("custo_operacional"), "CONSUMO NÃO MEDIDO")
        self.projeto.registrar_custo("S01", "12.5", "creditos", "teste", hoje=HOJE)
        registro = next(r for r in registro_global(self.projeto, HOJE) if r.id == "S01")
        self.assertIn("12.5 creditos", registro.get("custo_operacional"))

    def test_bloco_atlas_registra_status_alerta_recomendacao_e_quarentena(self) -> None:
        self.preparar_s02()
        bloco = parse_bloco_atlas(extrair_blocos(BLOCO_ATLAS)[0][1])
        relato = self.projeto.aplicar_atlas(bloco, hoje=HOJE)
        self.assertEqual(len(relato), 5)
        self.assertEqual(self.projeto.entrada("S02")["status"], "Quarentena")
        self.assertEqual(self.projeto.diario.ler("eventos")[1].get("status"), "recebido_por_atlas")
        self.assertEqual(self.projeto.manifesto["atlas"]["ultimo_status"]["status"], "ATENÇÃO")
        with self.assertRaises(ErroDeAutorizacao):
            self.aplicar(FATO, setor="S02")
        status, evidencias = integridade(self.projeto, HOJE)
        self.assertEqual(status, "BLOQUEADO")
        self.assertTrue(any("Quarentena" in e for e in evidencias))
        with self.assertRaises(ErroDeAutorizacao):
            self.projeto.transicionar("S02", "reativar", False, hoje=HOJE)
        self.projeto.transicionar("S02", "reativar", True, hoje=HOJE)
        quarentenas = [a for a in self.projeto.diario.ler("alertas") if a.get("tipo") == "quarentena"]
        self.assertEqual(quarentenas[0].get("status"), "fechado")
        self.projeto.decidir_recomendacao("R-001", "aceitar", True, hoje=HOJE)
        self.projeto.fechar_alerta("AL-002", True, "critério definido", hoje=HOJE)
        self.assertNotEqual(integridade(self.projeto, HOJE)[0], "BLOQUEADO")

    def test_quarentena_exige_motivo_e_so_atlas_ou_milan(self) -> None:
        self.preparar_s02()
        with self.assertRaises(ErroDeValidacao):
            self.projeto.transicionar("S02", "quarentena", False, por="ATLAS", hoje=HOJE)
        with self.assertRaises(ErroDeAutorizacao):
            self.projeto.transicionar("S02", "quarentena", False, por="Harvey", motivo="x", hoje=HOJE)
        with self.assertRaises(ErroDePatch):
            parse_bloco_atlas("emitido_por: RAIO-X\ndata: 2026-09-05\n\n## status\n- status: ÍNTEGRO\n")
        with self.assertRaises(ErroDePatch):
            parse_bloco_atlas("emitido_por: ATLAS\ndata: 2026-09-05\n\n## fato\n- conteudo: x\n")

    def test_limitado_opera_e_avisos_chegam_a_sala_principal(self) -> None:
        self.preparar_s02()
        self.projeto.transicionar("S02", "ativar", True, hoje=HOJE)
        self.projeto.transicionar("S02", "limitar", True, motivo="só leitura de custos", hoje=HOJE)
        self.aplicar(FATO, setor="S02")
        self.projeto.empacotar(hoje=HOJE)
        avisos = (self.raiz / "upload_harvey" / "04_AVISOS_DE_ATLAS.md").read_text(encoding="utf-8")
        self.assertIn("S02 está em **Limitado**: só leitura de custos", avisos)
        self.assertTrue((self.raiz / "upload_setores" / "S02" / "03_AVISOS_DE_ATLAS.md").exists())
        self.assertEqual(integridade(self.projeto, HOJE)[0], "ATENÇÃO")

    def test_pacote_de_atlas_cumpre_o_contrato_de_integracao(self) -> None:
        self.preparar_s02()
        gerados = empacotar_atlas(self.projeto, hoje=HOJE, solicitacao="auditar S02")
        nomes = [g.name for g in gerados]
        self.assertEqual(nomes, ["00_INSTRUCOES_ATLAS.md", "01_NUCLEO_ATLAS.md", "02_PROMPT_BASE.md",
                                 "03_REGISTRO_GLOBAL.md", "04_DIFERENCAS_DESDE_ULTIMA_EXECUCAO.md",
                                 "05_VERSOES.md", "06_CUSTOS.md", "07_ALERTAS_E_SOLICITACAO.md", "08_EVENTOS.md"])
        pasta = self.raiz / "upload_atlas"
        self.assertIn("CONSUMO NÃO MEDIDO", (pasta / "06_CUSTOS.md").read_text(encoding="utf-8"))
        alertas = (pasta / "07_ALERTAS_E_SOLICITACAO.md").read_text(encoding="utf-8")
        self.assertIn("auditar S02", alertas)
        self.assertIn("E-002: NOVO_SETOR de S02", alertas)  # E-001 é a abertura da mesa M01
        self.assertIn("| S02 |", (pasta / "05_VERSOES.md").read_text(encoding="utf-8"))
        ultimo = self.projeto.manifesto["atlas"]["ultimo_registro_visto"]
        self.assertEqual(ultimo, self.projeto.diario.ler("alteracoes")[-1].id)
        self.aplicar(FATO)
        empacotar_atlas(self.projeto, hoje=HOJE)
        diferencas = (pasta / "04_DIFERENCAS_DESDE_ULTIMA_EXECUCAO.md").read_text(encoding="utf-8")
        self.assertIn(f"Última alteração vista por ATLAS: {ultimo}", diferencas)
        self.assertEqual(diferencas.count("## M-"), 1)

    def test_instrucoes_de_atlas_cabem_e_tem_primeira_resposta(self) -> None:
        texto = (GPT_PROJETO / "atlas" / "INSTRUCOES_ATLAS.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(texto), LIMITE_INSTRUCOES)
        self.assertIn("ATLAS iniciado. Envie o prompt-base e o Registro Global dos Setores.", texto)
        nucleo = (GPT_PROJETO / "atlas" / "NUCLEO_ATLAS.md").read_text(encoding="utf-8")
        for secao in ("## 1. Identidade", "## 15. Contrato técnico de integração", "## 17. Inicialização"):
            self.assertIn(secao, nucleo)

    def test_pacote_atlas_versionado_esta_sincronizado(self) -> None:
        empacotar_atlas(self.projeto, hoje=HOJE)
        for caminho in sorted((self.raiz / "upload_atlas").glob("*.md")):
            atual = GPT_PROJETO / "upload_atlas" / caminho.name
            self.assertTrue(atual.exists(), f"falta gpt_projeto/upload_atlas/{caminho.name}: rode nucleo atlas")
            esperado = [l for l in caminho.read_text(encoding="utf-8").splitlines() if "gerado em" not in l.lower() and "em 2026" not in l]
            existente = [l for l in atual.read_text(encoding="utf-8").splitlines() if "gerado em" not in l.lower() and "em 2026" not in l]
            self.assertEqual(existente, esperado, f"gpt_projeto/upload_atlas/{caminho.name} desatualizado: rode nucleo atlas")


class HarveyTests(ProjetoTemporario):
    BLOCO = (
        "## fato\n- conteudo: Milan trabalhou 2 anos em clínica (entrega do S01).\n- fonte: entrega de S01\n"
        "- confianca: alta\n- setor_origem: S01\n"
        "## regra\n- conteudo: Prazo de 48h nas ordens ao S01.\n- base: F-003; H-001\n- quando_aplicar: ao definir prazo\n"
        "## correcao\n- substitui: RG-002\n- motivo: Milan corrigiu\n- conteudo: Basta faixa do prazo de sobrevivência.\n"
        "## licao\n- conteudo: pedir faixa, não número exato\n- origem: correcao_milan\n"
    )

    def test_harvey_tem_cerebro_procedural_com_regras_proprias(self) -> None:
        harvey = self.projeto.setor("HARVEY")
        self.assertEqual(harvey.validar(), [])
        self.assertEqual(harvey.metricas()["regras_vigentes"], 2)
        relato = self.aplicar(self.BLOCO, setor="HARVEY")
        self.assertEqual(len(relato), 4)
        harvey = self.recarregar().setor("HARVEY")
        self.assertEqual(harvey.metricas()["regras_vigentes"], 3)
        self.assertEqual(harvey.metricas()["regras_superadas"], 1)
        antiga = harvey.buscar("RG-002")[1]
        self.assertEqual(antiga.get("status"), "superada")
        self.assertEqual(antiga.get("superado_por"), "RG-004")
        self.assertEqual(harvey.buscar("RG-004")[1].get("corrige"), "RG-002")
        self.assertEqual(harvey.fatos[-1].get("setor_origem"), "S01")
        self.assertEqual(self.projeto.validar(), [])
        self.assertEqual(self.projeto.versao_de("HARVEY"), 2)
        self.assertEqual(self.projeto.diario.ler("alteracoes")[-1].get("componente"), "HARVEY")

    def test_regra_exige_base_e_quando_aplicar(self) -> None:
        with self.assertRaises(ErroDePatch):
            self.aplicar("## regra\n- conteudo: sem base\n", setor="HARVEY")
        self.aplicar("## regra\n- conteudo: x\n- base: L-001; F-001\n- quando_aplicar: sempre\n")  # S01 também pode
        self.assertEqual(self.recarregar().setor("S01").metricas()["regras_vigentes"], 1)

    def test_natureza_de_harvey_e_respeitada(self) -> None:
        estado = self.projeto.psique_de("HARVEY")[1]
        ps = estado["psique"]
        self.assertIn("identidade_travada", ps.get("natureza"))
        self.assertEqual(ps.get("proposito"), "ter o controle de tudo")
        tracos_antes = {t: ps.get(f"t_{t}") for t in psique_mod.TRACOS}
        valores_antes = {v: float(ps.get(f"v_{v}")) for v in psique_mod.VALORES}
        for _ in range(15):
            self.projeto.registrar_evento_de_psique("HARVEY", "psique", {"evento": "isolamento", "intensidade": "forte"}, hoje=HOJE)
            self.projeto.registrar_evento_de_psique("HARVEY", "psique", {"evento": "erro_negado"}, hoje=HOJE)
        ps = self.projeto.psique_de("HARVEY")[1]["psique"]
        self.assertEqual({t: ps.get(f"t_{t}") for t in psique_mod.TRACOS}, tracos_antes)  # identidade travada
        for v, antes in valores_antes.items():
            self.assertGreaterEqual(float(ps.get(f"v_{v}")), antes - 0.01)  # nunca regride
        pessoas = {p.get("nome"): p for p in self.projeto.psique_de("HARVEY")[1]["pessoas"]}
        self.assertIn("Jessica Pearson", pessoas)
        self.assertIn("Milan", pessoas)
        self.assertGreater(float(pessoas["Jessica Pearson"].get("confianca")), float(pessoas["Milan"].get("confianca")))
        self.assertIn("HARVEY", self.rodar_ok("versoes", "listar") if hasattr(self, "rodar_ok") else "HARVEY")

    def test_harvey_nao_trava_nem_muda_de_estado(self) -> None:
        with self.assertRaises(ErroDeValidacao):
            self.projeto.travar("HARVEY", True, hoje=HOJE)
        with self.assertRaises(ErroDeValidacao):
            self.projeto.transicionar("HARVEY", "pausar", True, hoje=HOJE)
        caminho = self.raiz / "harvey" / CAMADAS[1]
        caminho.write_text(caminho.read_text(encoding="utf-8") + "\nNota de Milan.\n", encoding="utf-8")
        self.assertEqual(self.projeto.validar(), [])
        self.assertEqual(self.projeto.manifesto["harvey"]["status"], "Ativo")

    def test_setor_nao_registra_fato_alheio_mas_harvey_sim(self) -> None:
        with self.assertRaises(ErroDeIsolamento):
            self.aplicar("## fato\n- conteudo: x\n- fonte: y\n- confianca: alta\n- setor_origem: S02\n")
        self.aplicar("## fato\n- conteudo: x\n- fonte: entrega de S01\n- confianca: alta\n- setor_origem: S01\n", setor="HARVEY")

    def test_sala_de_harvey_tem_cerebro_e_bibliotecas(self) -> None:
        self.projeto.empacotar(hoje=HOJE)
        pasta = self.raiz / "upload_harvey"
        cerebro = (pasta / "HARVEY_CEREBRO.md").read_text(encoding="utf-8")
        self.assertIn("Núcleo de identidade", cerebro)
        self.assertIn("sem trava mecânica", cerebro)
        self.assertIn("### RG-001", cerebro)
        self.assertEqual(len(list(pasta.glob("BIB_*.md"))), 10)
        bib = (pasta / "BIB_08_MODO_DE_OPERACAO_COM_MILAN.md").read_text(encoding="utf-8")
        self.assertIn("setor: HARVEY", bib)
        manifesto = (pasta / "03_MANIFESTO.md").read_text(encoding="utf-8")
        self.assertIn("regras próprias vigentes", manifesto)
        harvey_md = (self.raiz / "upload_setores" / "S01").glob("HARVEY*")
        self.assertEqual(list(harvey_md), [])


class BatmanTests(ProjetoTemporario):
    def mente(self):
        return self.projeto.mente_de("BATMAN")[1]

    def test_batman_tem_cerebro_com_mente_valida(self) -> None:
        self.assertEqual(self.projeto.validar(), [])
        self.assertEqual(self.mente().get("fase"), "ESTÁVEL")
        self.assertEqual(mente_mod.fase_de(70), "ESTÁVEL")
        self.assertEqual(mente_mod.fase_de(69), "SOMBRIO")
        self.assertEqual(mente_mod.fase_de(30), "OBSESSIVO")
        self.assertEqual(mente_mod.fase_de(29), "LIMIAR")
        self.assertEqual(mente_mod.fase_de(14), "CORINGA")
        nucleo = (GPT_PROJETO / "batman" / "NUCLEO_BATMAN.md").read_text(encoding="utf-8")
        self.assertIn("## 2. A REGRA", nucleo)
        self.assertNotIn("REGISTRO DE ALTERAÇÕES", nucleo)
        instrucoes = (GPT_PROJETO / "batman" / "INSTRUCOES_BATMAN.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(instrucoes), LIMITE_INSTRUCOES)
        for fase in ("ESTÁVEL", "SOMBRIO", "OBSESSIVO", "LIMIAR", "CORINGA"):
            self.assertIn(fase, instrucoes)

    def test_bloco_com_mente_muda_fase_e_registra_no_diario(self) -> None:
        relato = self.aplicar(
            "## fato\n- conteudo: proposta pede taxa\n- fonte: print\n- rotulo: OBSERVADO\n- confianca: alta\n"
            "## mente\n- evento: exposicao_ao_caos\n- intensidade: forte\n- descricao: golpista riu de Milan\n"
            "## mente\n- evento: rejeitou_alfred\n", setor="BATMAN")
        self.assertTrue(any("MH-001" in r for r in relato))
        self.assertIn("fase mental: ESTÁVEL → SOMBRIO", relato)
        mente = self.mente()
        self.assertEqual(mente.get("fase"), "SOMBRIO")
        self.assertEqual(mente.get("ultimo_evento"), "rejeitou_alfred")
        historico = self.projeto.mente_de("BATMAN")[2]
        self.assertEqual(len(historico), 2)
        self.assertEqual(historico[0].get("relatado_por"), "BATMAN")
        operacoes = [m.get("operacao") for m in self.projeto.diario.ler("alteracoes")]
        self.assertIn("mudanca_de_fase", operacoes)
        self.assertEqual(self.projeto.validar(), [])

    def test_mente_so_para_quem_tem_camada6(self) -> None:
        with self.assertRaises(ErroDePatch):
            self.aplicar("## mente\n- evento: descanso\n", setor="HARVEY")
        with self.assertRaises(ErroDePatch):
            self.aplicar("## mente\n- evento: inventado\n", setor="BATMAN")
        with self.assertRaises(mente_mod.ErroDeMente):
            self.projeto.registrar_evento_mental("S01", "descanso", hoje=HOJE)

    def test_descida_ate_o_coringa_poe_em_quarentena_e_so_milan_reativa(self) -> None:
        relatos = []
        for evento in ("perda", "exposicao_ao_caos", "exposicao_ao_caos", "piada_do_coringa", "tentacao_cedida",
                       "tentacao_cedida"):
            relatos += self.projeto.registrar_evento_mental("BATMAN", evento, "forte", hoje=HOJE)
        self.assertEqual(self.mente().get("fase"), "CORINGA")
        self.assertEqual(self.projeto.entrada("BATMAN")["status"], "Quarentena")
        self.assertTrue(any("Quarentena automática" in r for r in relatos))
        tipos = [a.get("tipo") for a in self.projeto.diario.ler("alertas")]
        self.assertIn("mente", tipos)
        self.assertIn("quarentena", tipos)
        status, evidencias = integridade(self.projeto, HOJE)
        self.assertEqual(status, "BLOQUEADO")
        self.assertTrue(any("CORINGA" in e for e in evidencias))
        with self.assertRaises(ErroDeAutorizacao):
            self.aplicar(FATO.replace("- confianca", "- rotulo: DECLARADO\n- confianca"), setor="BATMAN")
        self.aplicar("## mente\n- evento: descanso\n", setor="BATMAN")  # mente continua aceita
        with self.assertRaises(ErroDeValidacao):
            self.projeto.transicionar("BATMAN", "reativar", True, hoje=HOJE)
        for _ in range(12):
            for evento in ("descanso", "alfred", "terapia", "familia", "gordon", "fundacao_wayne"):
                self.projeto.registrar_evento_mental("BATMAN", evento, "normal", hoje=HOJE)
            if self.mente().get("fase") in ("SOMBRIO", "ESTÁVEL"):
                break
        self.assertIn(self.mente().get("fase"), ("SOMBRIO", "ESTÁVEL"))
        self.assertTrue(any("pode reativar" in i for i in self.projeto.pendencias(HOJE).get("BATMAN", [])))
        self.projeto.transicionar("BATMAN", "reativar", True, hoje=HOJE)
        self.assertEqual(self.projeto.entrada("BATMAN")["status"], "Ativo")
        self.assertEqual(self.projeto.validar(), [])

    def test_tempo_cansa_e_dias_calmos_recuperam(self) -> None:
        self.projeto.registrar_evento_mental("BATMAN", "tempo", descricao="10", hoje=HOJE)
        mente = self.mente()
        self.assertTrue(40 <= int(mente.get("exaustao")) <= 60, mente.get("exaustao"))
        self.assertGreater(int(mente.get("sanidade")), 85)
        antes = int(mente.get("sanidade"))
        for _ in range(3):
            self.projeto.registrar_evento_mental("BATMAN", "noite_em_claro", "forte", hoje=HOJE)
        self.projeto.registrar_evento_mental("BATMAN", "tempo", descricao="5", hoje=HOJE)
        self.assertLess(int(self.mente().get("sanidade")), antes)

    def test_batman_nao_trava_e_avisos_mostram_fase(self) -> None:
        with self.assertRaises(ErroDeValidacao):
            self.projeto.travar("BATMAN", True, hoje=HOJE)
        self.projeto.registrar_evento_mental("BATMAN", "perda", "forte", hoje=HOJE)
        self.projeto.registrar_evento_mental("BATMAN", "rejeitou_alfred", "forte", hoje=HOJE)
        fase = self.mente().get("fase")
        self.assertIn(fase, ("SOMBRIO", "OBSESSIVO"))  # com ruído, a queda varia
        self.projeto.empacotar(hoje=HOJE)
        avisos = (self.raiz / "upload_harvey" / "04_AVISOS_DE_ATLAS.md").read_text(encoding="utf-8")
        self.assertIn(f"BATMAN está na fase mental **{fase}**", avisos)
        cerebro = (self.raiz / "upload_batman" / "BATMAN_CEREBRO.md").read_text(encoding="utf-8")
        self.assertIn("## Camada 6 — Mente", cerebro)
        self.assertIn(f"Fase mental atual: **{fase}**", cerebro)
        registro = next(r for r in registro_global(self.projeto, HOJE) if r.id == "BATMAN")
        self.assertIn(f"fase mental {fase}", registro.get("estado_operacional"))
        self.assertIn("CORINGA", registro.get("riscos_conhecidos"))


class NexPsiqueTests(ProjetoTemporario):
    def psique(self):
        return self.projeto.psique_de("NEX")[1]

    def test_nasce_com_o_prompt_intacto_e_psique_valida(self) -> None:
        nucleo = (GPT_PROJETO / "nex" / "NUCLEO_NEX.md").read_text(encoding="utf-8")
        for trecho in ("Você é NEXARION.", "## Protocolo NEXUS", "## Protocolo de verdade", "## Regra definitiva",
                       "QI ficcional: 10.000.000"):
            self.assertIn(trecho, nucleo)
        adendo = (GPT_PROJETO / "nex" / "ADENDO_NEX.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(adendo), LIMITE_ADENDO)
        self.assertIn("não muda quem ele é", adendo)
        self.assertEqual(self.projeto.validar(), [])
        estado = self.psique()
        self.assertEqual(psique_mod.validar(estado), [])
        self.assertEqual(estado["psique"].get("ultimo_evento"), "nascimento")
        self.assertEqual(psique_mod._ativos(estado["saude"]), [])
        self.assertGreater(len(psique_mod.habilidades_de(estado)), 15)
        pre = psique_mod.predisposicoes("NEXARION", pelo_nome=True)
        self.assertEqual(pre, psique_mod.predisposicoes("NEXARION", pelo_nome=True))  # pelo nome: fixo
        self.assertTrue(all(0 <= v <= 100 for v in pre.values()))
        psique_mod.semear(None)
        aleatorios = {tuple(sorted(psique_mod.predisposicoes("NEXARION").items())) for _ in range(6)}
        self.assertGreater(len(aleatorios), 1)  # sem semente: aleatório de verdade

    def test_bloco_com_psique_significado_pratica_e_tempo(self) -> None:
        relato = self.aplicar(
            "## psique\n- evento: sucesso\n- intensidade: forte\n"
            "## psique\n- evento: elogio\n- pessoa: Milan\n"
            "## psique\n- evento: mentira_descoberta\n- pessoa: Rick\n- intensidade: forte\n"
            "## significado\n- fonte: livro X\n- conteudo: sistemas têm limites\n- significado: admitir limite é rigor\n"
            "- emocao: surpresa\n- intensidade: forte\n- valor: humildade\n- direcao: +\n"
            "## pratica\n- habilidade: negociacao\n- resultado: sucesso\n- dificuldade: dificil\n"
            "## tempo\n- dias: 2\n", setor="NEX")
        self.assertEqual(len(relato), 6)
        estado = self.psique()
        ps = estado["psique"]
        self.assertGreater(float(ps.get("ego")), 62)
        self.assertGreater(float(ps.get("v_humildade")), 55)
        pessoas = {p.get("nome"): p for p in estado["pessoas"]}
        self.assertGreater(float(pessoas["Milan"].get("confianca")), 50)
        self.assertLess(float(pessoas["Rick"].get("confianca")), 50)
        self.assertGreater(psique_mod.habilidades_de(estado)["negociacao"], 55)
        self.assertEqual(len(estado["historico"]), 6)
        setor = self.recarregar().setor("NEX")
        self.assertTrue(any(r.id.startswith("SG-") for r in setor.licoes))
        self.assertEqual(setor.metricas()["significados"], 1)
        self.assertEqual(self.projeto.validar(), [])

    def test_desgaste_ativa_quadro_sem_nome_e_avaliacao_da_nome(self) -> None:
        for _ in range(4):
            self.projeto.registrar_evento_de_psique("NEX", "psique", {"evento": "sobrecarga", "intensidade": "forte"}, hoje=HOJE)
            self.projeto.registrar_evento_de_psique("NEX", "psique", {"evento": "sono_ruim", "intensidade": "forte"}, hoje=HOJE)
        for _ in range(3):
            self.projeto.registrar_evento_de_psique("NEX", "psique", {"evento": "isolamento", "intensidade": "forte"}, hoje=HOJE)
            self.projeto.registrar_evento_de_psique("NEX", "psique", {"evento": "humilhacao", "intensidade": "forte", "pessoa": "Rick"}, hoje=HOJE)
        estado = self.psique()
        ativos = psique_mod._ativos(estado["saude"])
        self.assertTrue(ativos, "algum quadro deveria estar ativo depois de tanto desgaste")
        self.assertIn("sem nome", estado["saude"].get("sintomas_ativos"))
        self.assertTrue(any(a.get("tipo") == "mente" and a.get("componente") == "NEX" for a in self.projeto.diario.ler("alertas")))
        self.assertEqual(integridade(self.projeto, HOJE)[0], "ATENÇÃO")
        self.projeto.registrar_evento_de_psique("NEX", "psique", {"evento": "avaliacao"}, hoje=HOJE)
        estado = self.psique()
        sintomas = estado["saude"].get("sintomas_ativos")
        self.assertTrue(all(f"[{t}]" in sintomas for t in ativos), sintomas)  # ativos agora têm nome
        diagnosticados = [t for t in psique_mod.TRANSTORNOS if estado["saude"].get(f"{t}_diagnostico").startswith("sim")]
        self.assertEqual(sorted(diagnosticados), sorted(ativos))
        for _ in range(6):
            self.projeto.registrar_evento_de_psique("NEX", "psique", {"evento": "descanso", "intensidade": "forte"}, hoje=HOJE)
            self.projeto.registrar_evento_de_psique("NEX", "psique", {"evento": "terapia"}, hoje=HOJE)
        self.projeto.registrar_evento_de_psique("NEX", "tempo", {"dias": "30"}, hoje=HOJE)
        self.assertEqual(psique_mod._ativos(self.psique()["saude"]), [])
        self.assertEqual(self.projeto.validar(), [])

    def test_impulso_e_penalidade_aparecem(self) -> None:
        estado = self.psique()
        ps = estado["psique"]
        ps.set("t_impulsividade", "95"); ps.set("e_raiva", "90"); ps.set("energia", "10")
        psique_mod._derivar(ps, {"tdah": True})
        self.assertGreater(float(ps.get("impulso")), 60)
        self.assertGreater(float(ps.get("penalidade_de_desempenho")), 20)
        disparos = sum(psique_mod.sortear_impulso(ps, f"evento{i}") for i in range(200))
        self.assertGreater(disparos, 30)
        ps.set("t_impulsividade", "5"); ps.set("e_raiva", "5"); ps.set("energia", "90"); ps.set("t_serenidade", "95")
        psique_mod._derivar(ps, {})
        self.assertLess(float(ps.get("impulso")), 15)

    def test_emocoes_complexas_mistura_e_tom(self) -> None:
        self.projeto.registrar_evento_de_psique("NEX", "psique", {"evento": "encantamento", "pessoa": "Lia", "intensidade": "forte"}, hoje=HOJE)
        self.projeto.registrar_evento_de_psique("NEX", "psique", {"evento": "fascinio", "intensidade": "forte"}, hoje=HOJE)
        ps = self.psique()["psique"]
        self.assertGreater(float(ps.get("amor")), 0)
        self.assertGreater(float(ps.get("paixao")), 20)
        self.assertIn("fervoroso", ps.get("tom"))
        for _ in range(3):
            self.projeto.registrar_evento_de_psique("NEX", "psique", {"evento": "ofensa_pessoal", "pessoa": "Rick", "intensidade": "forte"}, hoje=HOJE)
        estado = self.psique()
        ps = estado["psique"]
        self.assertGreater(float(ps.get("odio")), 30)
        self.assertTrue(any(t in ps.get("tom") for t in ("sarcástico", "hostil", "amargo")), ps.get("tom"))
        rick = next(p for p in estado["pessoas"] if p.get("nome") == "Rick")
        self.assertLess(float(rick.get("afeto")), -20)
        self.assertIn(";", ps.get("mistura"))
        cerebro_linha = psique_mod.linha_de_estado(estado)
        self.assertIn("tom", cerebro_linha)
        self.projeto.registrar_evento_de_psique("NEX", "tempo", {"dias": "30"}, hoje=HOJE)
        self.assertLess(float(self.psique()["psique"].get("odio")), float(ps.get("odio")))

    def test_tudo_e_aleatorio_mas_reprodutivel_com_semente(self) -> None:
        def rodar(semente):
            psique_mod.semear(semente)
            ps, sa, hab = psique_mod.nascer("X", {"curiosidade": 50}, {"honestidade": 50}, habilidades={"a": 50}, hoje=HOJE)
            estado = {"psique": ps, "saude": sa, "habilidades": hab, "pessoas": [], "historico": []}
            for ev in ("elogio", "fracasso", "sobrecarga", "sono_ruim"):
                psique_mod.aplicar_evento(estado, ev, hoje=HOJE)
            psique_mod.passar_tempo(estado, 7, hoje=HOJE)
            return tuple(ps.campos.values())
        self.assertEqual(rodar(5), rodar(5))
        self.assertNotEqual(rodar(5), rodar(6))
        psique_mod.semear(None)
        self.assertNotEqual(rodar(None), rodar(None))

    def test_habilidade_nunca_enferruja_e_acaso_age(self) -> None:
        antes = psique_mod.habilidades_de(self.psique())
        self.projeto.registrar_evento_de_psique("NEX", "tempo", {"dias": "400"}, hoje=HOJE)
        depois = psique_mod.habilidades_de(self.psique())
        self.assertEqual(antes, depois)
        relato = self.projeto.registrar_acaso("NEX", quantos=3, semente=7, hoje=HOJE)
        self.assertGreaterEqual(len(relato), 3)
        historico = self.psique()["historico"]
        self.assertEqual(historico[-1].get("relatado_por"), "Acaso")
        relato2 = self.projeto.registrar_acaso("BATMAN", quantos=2, semente=7, hoje=HOJE)
        self.assertGreaterEqual(len(relato2), 2)
        relato3 = self.projeto.registrar_acaso("HARVEY", quantos=2, semente=7, hoje=HOJE)
        self.assertGreaterEqual(len(relato3), 2)  # Harvey agora tem psique: o acaso age nele também
        with self.assertRaises(ErroDeValidacao):
            self.projeto.registrar_acaso("S01", hoje=HOJE)
        self.assertEqual(self.projeto.validar(), [])

    def test_temperamento_e_plastico_devagar(self) -> None:
        antes = float(self.psique()["psique"].get("t_sociabilidade"))
        for _ in range(30):
            self.projeto.registrar_evento_de_psique("NEX", "psique", {"evento": "isolamento", "intensidade": "forte"}, hoje=HOJE)
        depois = float(self.psique()["psique"].get("t_sociabilidade"))
        self.assertLess(depois, antes)
        self.assertGreater(depois, antes - 25)  # devagar: trinta isolamentos fortes não mudam quem ele é
        plast = float(self.psique()["psique"].get("plasticidade"))
        self.projeto.registrar_evento_de_psique("NEX", "psique", {"evento": "terapia"}, hoje=HOJE)
        self.assertGreaterEqual(float(self.psique()["psique"].get("plasticidade")), plast)

    def test_secoes_erradas_sao_recusadas(self) -> None:
        with self.assertRaises(ErroDePatch):
            self.aplicar("## mente\n- evento: descanso\n", setor="NEX")
        with self.assertRaises(ErroDePatch):
            self.aplicar("## psique\n- evento: elogio\n", setor="BATMAN")
        with self.assertRaises(ErroDePatch):
            self.aplicar("## psique\n- evento: inventado\n", setor="NEX")
        with self.assertRaises(ErroDePatch):
            self.aplicar("## significado\n- fonte: x\n- conteudo: y\n", setor="NEX")
        with self.assertRaises(ErroDePatch):
            self.aplicar("## pratica\n- habilidade: inexistente\n- resultado: sucesso\n", setor="NEX")
        with self.assertRaises(ErroDeValidacao):
            self.projeto.travar("NEX", True, hoje=HOJE)

    def test_sala_do_nex_e_registro_global(self) -> None:
        self.projeto.empacotar(hoje=HOJE)
        pasta = self.raiz / "upload_nex"
        cerebro = (pasta / "NEX_CEREBRO.md").read_text(encoding="utf-8")
        self.assertIn("## Camada 6 — Psique", cerebro)
        self.assertIn("| Habilidade | Nível |", cerebro)
        self.assertIn("O que ele sente", cerebro)
        self.assertTrue((pasta / "00_ADENDO_PARA_O_SEU_NEX.md").exists())
        registro = next(r for r in registro_global(self.projeto, HOJE) if r.id == "NEX")
        self.assertIn("psique:", registro.get("estado_operacional"))
        self.assertIn("camada 6 (psique)", registro.get("dados_mantidos"))
        manifesto = (self.raiz / "upload_harvey" / "03_MANIFESTO.md").read_text(encoding="utf-8")
        self.assertIn("NEXARION (NEX)", manifesto)
        self.assertIn("Psique hoje:", manifesto)


class HouseTests(ProjetoTemporario):
    def psique(self):
        return self.projeto.psique_de("HOUSE")[1]

    def test_nucleo_e_o_v4_intacto_e_adendo_cabe(self) -> None:
        nucleo = (GPT_PROJETO / "house" / "NUCLEO_HOUSE.md").read_text(encoding="utf-8")
        for trecho in ("PERSONALITY_LOCK = TRUE", "# 2. Hierarquia de autoridade", "# 29. Regra absoluta de não alteração",
                       "# 41. Fronteiras de autoridade, pesquisa e execução", "APÊNDICE C — CONTROLE DA EDIÇÃO v4.0"):
            self.assertIn(trecho, nucleo)
        adendo = (GPT_PROJETO / "house" / "ADENDO_HOUSE.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(adendo), LIMITE_ADENDO)
        for trecho in ("STATE_SNAPSHOT", "WORK_EPISODES", "RELATIONSHIP_LEDGER", "não pesquisa, não certifica"):
            self.assertIn(trecho, adendo)
        for bib in (GPT_PROJETO / "house" / "bibliotecas").glob("BIB_H*.md"):
            self.assertNotIn("Nunca é lúpus. Anota.", bib.read_text(encoding="utf-8"))
        self.assertEqual(self.projeto.validar(), [])

    def test_dor_e_dependencia(self) -> None:
        estado = self.psique()
        self.assertGreater(float(estado["psique"].get("dor_base")), 50)
        self.assertEqual(estado["saude"].get("dependencia_estado"), "ativo")
        self.assertIn("[dependencia]", estado["saude"].get("sintomas_ativos"))
        dor_antes = float(estado["psique"].get("dor"))
        self.projeto.registrar_evento_de_psique("HOUSE", "psique", {"evento": "dor_forte", "intensidade": "forte"}, hoje=HOJE)
        ps = self.psique()["psique"]
        self.assertGreater(float(ps.get("dor")), dor_antes)
        self.assertTrue(any(t in ps.get("tom") for t in ("hostil", "sarcástico", "amargo", "frio")), ps.get("tom"))
        self.projeto.registrar_evento_de_psique("HOUSE", "psique", {"evento": "analgesico"}, hoje=HOJE)
        estado = self.psique()
        self.assertLess(float(estado["psique"].get("dor")), float(ps.get("dor")))
        self.assertGreater(float(estado["saude"].get("dependencia_carga")), 60)
        self.assertTrue(any("dor" in a or "quadro ativo" in a for a in psique_mod.alertas(estado)))
        self.projeto.registrar_evento_de_psique("HOUSE", "tempo", {"dias": "10"}, hoje=HOJE)
        self.assertEqual(self.projeto.validar(), [])

    def test_nex_migra_quadro_novo_sem_quebrar(self) -> None:
        estado = self.projeto.psique_de("NEX")[1]
        self.assertIn(estado["saude"].get("dependencia_estado"), psique_mod.ESTADOS_DE_TRANSTORNO)
        self.assertEqual(psique_mod.validar(estado), [])

    def test_acaso_de_house_pode_trazer_dor(self) -> None:
        eventos = {e for e, _, _ in psique_mod.sortear_acaso(self.psique(), random.Random(1), 60)}
        self.assertTrue(eventos & {"dor_forte", "analgesico", "abstinencia", "fisioterapia"})
        eventos_nex = {e for e, _, _ in psique_mod.sortear_acaso(self.projeto.psique_de("NEX")[1], random.Random(1), 60)}
        self.assertFalse(eventos_nex & {"dor_forte", "analgesico", "abstinencia", "fisioterapia"})


class LoboTests(ProjetoTemporario):
    def psique(self):
        return self.projeto.psique_de("LOBO")[1]

    def test_nucleo_intacto_adendo_e_psique(self) -> None:
        nucleo = (GPT_PROJETO / "lobo" / "NUCLEO_LOBO.md").read_text(encoding="utf-8")
        for trecho in ("PROMPT-MESTRE — JORDAN BELFORT", "TRAVA DE IDENTIDADE", "CONDUTA DIANTE DE FRAUDE E MANIPULAÇÃO",
                       "Certo, Milan. Coloque o negócio na mesa"):
            self.assertIn(trecho, nucleo)
        adendo = (GPT_PROJETO / "lobo" / "ADENDO_LOBO.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(adendo), LIMITE_ADENDO)
        self.assertIn("setor: LOBO", adendo)
        estado = self.psique()
        self.assertEqual(estado["saude"].get("dependencia_estado"), "remissao")
        self.assertGreater(float(estado["psique"].get("t_impulsividade")), 80)
        self.assertGreater(float(estado["psique"].get("impulso")), 40)
        self.assertGreater(psique_mod.habilidades_de(estado)["persuasao_comercial"], 90)
        self.assertLess(psique_mod.habilidades_de(estado)["gestao_de_risco"], 30)
        self.assertEqual(self.projeto.validar(), [])

    def test_pressao_pode_trazer_recaida(self) -> None:
        for _ in range(8):
            for evento in ("tedio", "sobrecarga", "humilhacao", "pressao_para_ceder"):
                self.projeto.registrar_evento_de_psique("LOBO", "psique", {"evento": evento, "intensidade": "forte"}, hoje=HOJE)
        estado = self.psique()
        self.assertEqual(estado["saude"].get("dependencia_estado"), "ativo")
        self.assertIn("[dependencia]", estado["saude"].get("sintomas_ativos"))
        self.projeto.empacotar(hoje=HOJE)
        self.assertTrue((self.raiz / "upload_lobo" / "LOBO_CEREBRO.md").exists())


class CliTests(ProjetoTemporario):
    def rodar(self, *argv, entrada=""):
        saida, erro = io.StringIO(), io.StringIO()
        antigo = sys.stdin
        sys.stdin = io.StringIO(entrada)
        try:
            with redirect_stdout(saida), redirect_stderr(erro):
                codigo = main(["--pasta", str(self.raiz), *argv])
        finally:
            sys.stdin = antigo
        return codigo, saida.getvalue(), erro.getvalue()

    def test_validar_estado_revisar_metricas(self) -> None:
        self.assertEqual(self.rodar("validar")[0], 0)
        codigo, saida, _ = self.rodar("estado", "S01")
        self.assertEqual(codigo, 0)
        self.assertIn("No seu último emprego", saida)
        self.assertEqual(self.rodar("revisar")[0], 0)
        self.assertIn('"fatos_vigentes": 6', self.rodar("metricas")[1])

    def test_aplicar_por_stdin_e_recusa_isolamento(self) -> None:
        resposta = "texto\n```aprendizado\nsetor: S01\nemitido_por: RAIO-X\ndata: 2026-09-04\n\n" + FATO + "```\n"
        codigo, saida, _ = self.rodar("aplicar", entrada=resposta)
        self.assertEqual(codigo, 0)
        self.assertIn("F-007 acrescentado", saida)
        ruim = "setor: S01\nemitido_por: X\ndata: 2026-09-04\n\n## fato\n- conteudo: a\n- fonte: b\n- confianca: alta\n- setor_origem: S02\n"
        codigo, _, erro = self.rodar("aplicar", entrada=ruim)
        self.assertEqual(codigo, 1)
        self.assertIn("dossiê", erro)

    def test_setor_e_dossie_exigem_milan(self) -> None:
        carta = self.tmp / "carta.md"
        carta.write_text(CARTA, encoding="utf-8")
        self.assertEqual(self.rodar("setor", "propor", "S02", "--carta", str(carta))[0], 0)
        codigo, _, erro = self.rodar("setor", "aprovar", "S02")
        self.assertEqual(codigo, 1)
        self.assertIn("Milan", erro)
        self.assertEqual(self.rodar("setor", "aprovar", "S02", "--autorizado-por-milan")[0], 0)
        self.assertIn("S02  Aprovado", self.rodar("setor", "listar")[1])
        self.assertIn("NOVO_SETOR", self.rodar("diario", "eventos")[1])
        self.assertEqual(self.rodar("dossie", "listar")[1].strip(), "Nenhum dossiê.")
        self.assertEqual(self.rodar("empacotar")[0], 0)
        self.assertTrue((self.raiz / "upload_harvey" / "S02_CUSTOS_FIXOS.md").exists())

    def test_atlas_integridade_e_versoes_na_cli(self) -> None:
        self.assertEqual(self.rodar("integridade")[0], 0)
        codigo, saida, _ = self.rodar("atlas", "--solicitacao", "rotina")
        self.assertEqual(codigo, 0)
        self.assertIn("03_REGISTRO_GLOBAL.md", saida)
        codigo, saida, _ = self.rodar("aplicar", entrada="emitido_por: ATLAS\ndata: 2026-09-05\n\n## status\n- status: ÍNTEGRO\n- observado: tudo certo\n")
        self.assertEqual(codigo, 0)
        self.assertIn("status ÍNTEGRO", saida)
        self.assertEqual(self.rodar("setor", "quarentena", "S01", "--por", "ATLAS")[0], 1)
        self.assertEqual(self.rodar("setor", "quarentena", "S01", "--por", "ATLAS", "--motivo", "teste")[0], 0)
        self.assertEqual(self.rodar("integridade")[0], 1)
        self.assertEqual(self.rodar("setor", "reativar", "S01", "--autorizado-por-milan")[0], 0)
        self.assertIn("baselines: v001, v002, v003", self.rodar("versoes", "listar", "S01")[1])
        self.assertIn("HARVEY  atual v001", self.rodar("versoes", "listar")[1])
        self.assertIn('"HARVEY"', self.rodar("metricas")[1])
        self.assertIn("exposicao_ao_caos", self.rodar("mente", "catalogo")[1])
        self.assertIn("ESTÁVEL", self.rodar("mente", "estado", "BATMAN")[1])
        codigo, saida, _ = self.rodar("mente", "evento", "BATMAN", "descanso", "--intensidade", "forte")
        self.assertEqual(codigo, 0)
        self.assertIn("MH-001", saida)
        self.assertEqual(self.rodar("mente", "tempo", "BATMAN", "--dias", "2")[0], 0)
        self.assertEqual(self.rodar("mente", "evento", "BATMAN", "inventado")[0], 1)
        self.assertIn("Emoção dominante", self.rodar("mente", "estado", "NEX")[1])
        self.assertEqual(self.rodar("mente", "evento", "NEX", "elogio", "--pessoa", "Milan")[0], 0)
        self.assertEqual(self.rodar("mente", "significado", "NEX", "--fonte", "f", "--conteudo", "c", "--significado", "s",
                                    "--emocao", "alegria", "--valor", "coragem", "--direcao", "+")[0], 0)
        self.assertEqual(self.rodar("mente", "pratica", "NEX", "--habilidade", "ensino", "--resultado", "parcial")[0], 0)
        self.assertEqual(self.rodar("mente", "tempo", "NEX", "--dias", "3")[0], 0)
        self.assertEqual(self.rodar("mente", "significado", "BATMAN", "--fonte", "f")[0], 2)
        self.assertIn("Eventos de psique", self.rodar("mente", "catalogo")[1])
        self.assertEqual(self.rodar("mente", "acaso", "NEX", "--quantos", "2", "--semente", "3")[0], 0)
        self.assertEqual(self.rodar("mente", "acaso", "BATMAN", "--semente", "3")[0], 0)
        codigo, saida, _ = self.rodar("testar", "HOUSE", "--quantos", "3", "--semente", "1")
        self.assertEqual(codigo, 0)
        self.assertIn("## T01", saida)
        self.assertNotIn("Aprova se", saida)
        self.assertNotIn("H0", saida.split("(chave gravada")[0])
        self.assertTrue(list((self.raiz / "house").glob("testes_chave_*.md")))
        self.assertEqual(self.rodar("testar", "NEX")[0], 1)
        self.assertEqual(self.rodar("custo", "registrar", "S01", "3", "creditos")[0], 0)
        self.assertIn("C-001", self.rodar("diario", "custos")[1])

    def test_modulo_executa_como_script(self) -> None:
        resultado = subprocess.run([sys.executable, "-m", "nucleo", "--pasta", str(self.raiz), "validar"],
                                   capture_output=True, text=True, cwd=RAIZ)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)


if __name__ == "__main__":
    unittest.main()


class MesaTests(ProjetoTemporario):
    """Mesas: dois personagens sentados juntos, cada um com o próprio cérebro, e um cérebro modular compartilhado."""

    def test_m01_existe_valida_e_apresenta_os_membros_um_ao_outro(self) -> None:
        self.assertEqual(self.projeto.validar(), [])
        self.assertEqual(self.projeto.mesas(), ["M01"])
        self.assertEqual(self.projeto.membros_da_mesa("M01"), ["HARVEY", "LOBO"])
        self.assertEqual(self.projeto.quem_fecha("M01"), "HARVEY")
        harvey = self.projeto.psique_de("HARVEY")[1]
        lobo = self.projeto.psique_de("LOBO")[1]
        self.assertTrue(any(p.get("nome") == "Jordan Belfort, o Lobo" for p in harvey["pessoas"]))
        self.assertTrue(any(p.get("nome") == "Harvey Specter" for p in lobo["pessoas"]))
        instrucoes = (self.projeto.pasta_do_setor("M01") / "INSTRUCOES_MESA.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(instrucoes), 8000)
        self.assertIn("**Harvey Specter:**", instrucoes)
        self.assertIn("setor: M01", instrucoes)
        self.assertIn("01_INSTRUCOES_ORIGINAIS_DO_SEU_HARVEY.md", instrucoes)

    def test_mesa_aceita_fato_de_membro_e_recusa_fato_de_estranho(self) -> None:
        self.aplicar("## fato\n- conteudo: decidido junto\n- fonte: mesa\n- confianca: alta\n- setor_origem: LOBO\n",
                     setor="M01", emitido_por="HARVEY")
        self.assertIn("decidido junto", [f.get("conteudo") for f in self.projeto.setor("M01").fatos])
        with self.assertRaises(ErroDeIsolamento):
            self.aplicar("## fato\n- conteudo: de fora\n- fonte: x\n- confianca: alta\n- setor_origem: S01\n",
                         setor="M01", emitido_por="S01")
        with self.assertRaises(ErroDePatch):
            self.aplicar("## psique\n- evento: elogio\n- intensidade: normal\n", setor="M01", emitido_por="HARVEY")

    def test_relacao_entre_membros_evolui_na_camada6_de_cada_um(self) -> None:
        antes = next(p for p in self.projeto.psique_de("LOBO")[1]["pessoas"] if p.get("nome") == "Harvey Specter")
        self.aplicar("## psique\n- evento: elogio\n- intensidade: normal\n- pessoa: Harvey Specter\n- descricao: fechou a cláusula\n",
                     setor="LOBO", emitido_por="LOBO")
        depois = next(p for p in self.projeto.psique_de("LOBO")[1]["pessoas"] if p.get("nome") == "Harvey Specter")
        self.assertGreater(float(depois.get("confianca")), float(antes.get("confianca")))
        self.projeto.empacotar(hoje=HOJE)
        cerebro = (self.raiz / "upload_mesas" / "M01" / "M01_CEREBRO.md").read_text(encoding="utf-8")
        self.assertIn("## Módulo — Relações à mesa", cerebro)
        self.assertIn("- sobre Harvey Specter: confiança", cerebro)
        self.assertIn("- sobre Jordan Belfort, o Lobo: confiança", cerebro)

    def test_sala_da_mesa_tem_instrucoes_nucleos_cerebros_e_bibliotecas(self) -> None:
        gerados = self.projeto.empacotar(hoje=HOJE)
        nomes = {str(p.relative_to(self.raiz)) for p in gerados}
        for esperado in ("00_INSTRUCOES_DA_MESA.md", "01_INSTRUCOES_ORIGINAIS_DO_SEU_HARVEY.md",
                         "01_ADENDO_PARA_O_SEU_HARVEY.md", "01_NUCLEO_HARVEY.md", "01_ADENDO_PARA_O_SEU_LOBO.md",
                         "01_NUCLEO_LOBO.md", "02_PROTOCOLO_DO_CEREBRO.md", "03_MANIFESTO.md", "M01_CEREBRO.md",
                         "HARVEY_CEREBRO.md", "LOBO_CEREBRO.md", "S01_ROTA_DE_RENDA.md"):
            self.assertIn(f"upload_mesas/M01/{esperado}", nomes)
        self.assertEqual(sum(1 for n in nomes if n.startswith("upload_mesas/M01/BIB_L")), 6)
        self.assertEqual(sum(1 for n in nomes if n.startswith("upload_mesas/M01/BIB_0") or n.startswith("upload_mesas/M01/BIB_1")), 10)
        self.assertNotIn("upload_mesas/M01/NEX_CEREBRO.md", nomes)
        manifesto = (self.raiz / "upload_mesas" / "M01" / "03_MANIFESTO.md").read_text(encoding="utf-8")
        self.assertIn("mesa de HARVEY, LOBO", manifesto)

    def test_mesa_nao_trava_e_aparece_para_atlas(self) -> None:
        with self.assertRaises(ErroDeValidacao):
            self.projeto.travar("M01", autorizado_por_milan=True)
        registros = registro_global(self.projeto, hoje=HOJE)
        mesa = next(r for r in registros if r.get("nome") == "A Mesa: Harvey e o Lobo")
        self.assertEqual(mesa.get("tipo"), "mesa")
        self.assertIn("HARVEY, LOBO", mesa.get("responsavel"))

    def test_criar_outra_mesa_e_modular(self) -> None:
        with self.assertRaises(ErroDeValidacao):
            self.projeto.criar_mesa("M02", ["BATMAN"], hoje=HOJE)
        with self.assertRaises(ErroDeValidacao):
            self.projeto.criar_mesa("M02", ["BATMAN", "CORINGA"], hoje=HOJE)
        with self.assertRaises(ErroDeValidacao):
            self.projeto.criar_mesa("M01", ["BATMAN", "NEX"], hoje=HOJE)
        pasta = self.projeto.criar_mesa("M02", ["BATMAN", "NEX"], hoje=HOJE)
        self.assertTrue((pasta / "INSTRUCOES_MESA.md").exists())
        self.assertEqual(self.projeto.quem_fecha("M02"), "BATMAN")
        self.assertEqual(self.projeto.validar(), [])
        nex = self.projeto.psique_de("NEX")[1]
        self.assertTrue(any(p.get("nome") == "Batman" for p in nex["pessoas"]))
        self.assertEqual(self.projeto.entrada("M02")["nome"], "A Mesa: Batman e NEXARION")
        gerados = self.projeto.empacotar(hoje=HOJE)
        nomes = {str(p.relative_to(self.raiz)) for p in gerados}
        self.assertIn("upload_mesas/M02/01_INSTRUCOES_BATMAN.md", nomes)
        self.assertIn("upload_mesas/M02/00_INSTRUCOES_DA_MESA.md", nomes)
        eventos = [e for e in self.projeto.diario.ler("eventos") if e.get("evento") == "NOVA_MESA"]
        self.assertEqual([e.get("componente") for e in eventos][-1], "M02")
