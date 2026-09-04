import io
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
from nucleo.__main__ import main
from nucleo.patch import extrair_blocos
from nucleo.projeto import LIMITE_INSTRUCOES, SECOES_DA_CARTA
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
CARTA = "\n".join(
    f"## {secao}\n{'Custos Fixos' if secao == 'Nome' else 'texto'}\n" for secao in SECOES_DA_CARTA
)


class ProjetoTemporario(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.raiz = self.tmp / "gp"
        shutil.copytree(GPT_PROJETO, self.raiz, ignore=shutil.ignore_patterns("upload"))
        self.projeto = Projeto.abrir(self.raiz)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def aplicar(self, corpo, setor="S01", autorizado=False):
        return self.projeto.aplicar(bloco(setor, corpo=corpo), autorizado_por_milan=autorizado, hoje=HOJE)

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
        self.assertEqual(parse_bloco(blocos[0]).secoes[0].tipo, "fato")

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
        texto = (GPT_PROJETO / "INSTRUCOES_DO_PROJETO.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(texto), LIMITE_INSTRUCOES)
        self.assertIn("No seu último emprego, o que você fazia no dia a dia?", texto)

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
        self.assertEqual(self.projeto.pendencias(HOJE), {})
        depois = date(2026, 9, 20)
        itens = self.projeto.pendencias(depois)["S01"]
        self.assertTrue(any(i.startswith("F-003") for i in itens))
        self.assertTrue(any(i.startswith("H-001") for i in itens))
        self.assertTrue(any(i.startswith("ESTADO: prazo") for i in itens))

    def test_empacotar_gera_arquivos_para_o_projeto(self) -> None:
        gerados = self.projeto.empacotar(hoje=HOJE)
        nomes = [g.name for g in gerados]
        self.assertEqual(nomes, ["00_INSTRUCOES_DO_PROJETO.md", "01_PROTOCOLO_DO_CEREBRO.md",
                                 "02_MANIFESTO.md", "S01_ROTA_DE_RENDA.md"])
        setor_md = (self.raiz / "upload" / "S01_ROTA_DE_RENDA.md").read_text(encoding="utf-8")
        for trecho in ("## Camada 1", "### Missão", "### F-001", "### H-001", "### L-001", "### ESTADO",
                       "hash camada 1"):
            self.assertIn(trecho, setor_md)
        manifesto = (self.raiz / "upload" / "02_MANIFESTO.md").read_text(encoding="utf-8")
        self.assertIn("| S01 | Rota de Renda | Ativo |", manifesto)
        self.assertIn("Nenhuma pendência", manifesto)

    def test_empacotar_recusa_projeto_invalido(self) -> None:
        caminho = self.raiz / "setores" / "S01_rota_de_renda" / CAMADAS[1]
        caminho.write_text(caminho.read_text(encoding="utf-8") + "x\n", encoding="utf-8")
        with self.assertRaises(ErroDeValidacao):
            self.projeto.empacotar(hoje=HOJE)

    def test_pacote_versionado_esta_sincronizado_com_as_camadas(self) -> None:
        """O upload/ commitado deve refletir as camadas atuais (rode `nucleo empacotar`)."""
        gerado = (self.raiz / "upload")
        self.projeto.empacotar(hoje=HOJE)
        for caminho in sorted(gerado.glob("*.md")):
            atual = (GPT_PROJETO / "upload" / caminho.name)
            self.assertTrue(atual.exists(), f"falta gpt_projeto/upload/{caminho.name}: rode nucleo empacotar")
            esperado = [l for l in caminho.read_text(encoding="utf-8").splitlines() if "gerado em" not in l.lower()]
            existente = [l for l in atual.read_text(encoding="utf-8").splitlines() if "gerado em" not in l.lower()]
            self.assertEqual(existente, esperado, f"gpt_projeto/upload/{caminho.name} desatualizado: rode nucleo empacotar")


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
        self.assertEqual(self.rodar("dossie", "listar")[1].strip(), "Nenhum dossiê.")
        self.assertEqual(self.rodar("empacotar")[0], 0)
        self.assertTrue((self.raiz / "upload" / "S02_CUSTOS_FIXOS.md").exists())

    def test_modulo_executa_como_script(self) -> None:
        resultado = subprocess.run([sys.executable, "-m", "nucleo", "--pasta", str(self.raiz), "validar"],
                                   capture_output=True, text=True, cwd=RAIZ)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)


if __name__ == "__main__":
    unittest.main()
