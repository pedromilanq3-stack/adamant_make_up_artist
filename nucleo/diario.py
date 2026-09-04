"""Diário de alterações, versões e eventos: nada muda em silêncio.

- `diario/alteracoes.md`  M-nnn  toda mudança relevante, com versão anterior e nova,
                                 diferença, motivo, responsável e autorização
- `versoes/<comp>/vNNN/`         cópia dos arquivos do componente antes de cada mudança
                                 (baseline para reversão)
- `diario/eventos.md`     E-nnn  eventos que ATLAS precisa receber (NOVO_SETOR, MUDANCA_DE_NUCLEO)
- `diario/alertas.md`     AL-nnn alertas e auditorias emitidos por ATLAS
- `diario/recomendacoes.md` R-nnn recomendações priorizadas de ATLAS
- `diario/custos.md`      C-nnn  consumo registrado por Milan; sem registro, CONSUMO NÃO MEDIDO
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from .registros import Registro, parse_registros, proximo_id, render_registros

ARQUIVOS = {
    "alteracoes": ("M", "# Diário de alterações\n\nRegistro append-only. Correções são acrescentadas; "
                        "nada é apagado para fingir que o erro não existiu."),
    "eventos": ("E", "# Eventos para ATLAS\n\nATLAS só reconhece o que recebeu por evento ou pelo "
                     "Registro Global."),
    "alertas": ("AL", "# Alertas e auditorias de ATLAS\n\nCada alerta é sustentado por evidência."),
    "recomendacoes": ("R", "# Recomendações de ATLAS\n\nClassificadas por impacto, urgência, "
                           "confiança, esforço, custo, risco e reversibilidade."),
    "custos": ("C", "# Registro de custos\n\nSó consumo real informado por Milan. Sem registro, o "
                    "sistema declara CONSUMO NÃO MEDIDO."),
}
NAO_INFORMADO = "não informado"


class Diario:
    def __init__(self, raiz: Path) -> None:
        self.raiz = Path(raiz)
        self.pasta = self.raiz / "diario"
        self.pasta_versoes = self.raiz / "versoes"

    # ------------------------------------------------------------- leitura
    def _caminho(self, nome: str) -> Path:
        return self.pasta / f"{nome}.md"

    def ler(self, nome: str) -> list[Registro]:
        caminho = self._caminho(nome)
        if not caminho.exists():
            return []
        return parse_registros(caminho.read_text(encoding="utf-8"))[1]

    def buscar(self, nome: str, id_registro: str) -> Registro | None:
        for registro in self.ler(nome):
            if registro.id == id_registro:
                return registro
        return None

    # ------------------------------------------------------------- escrita
    def acrescentar(self, nome: str, campos: dict[str, str]) -> Registro:
        prefixo, _ = ARQUIVOS[nome]
        registros = self.ler(nome)
        registro = Registro(proximo_id(prefixo, registros), dict(campos))
        self._gravar(nome, registros + [registro])
        return registro

    def atualizar(self, nome: str, registro: Registro) -> None:
        registros = [r for r in self.ler(nome) if r.id != registro.id] + [registro]
        registros.sort(key=lambda r: (len(r.id), r.id))
        self._gravar(nome, registros)

    def _gravar(self, nome: str, registros: list[Registro]) -> None:
        self.pasta.mkdir(parents=True, exist_ok=True)
        _, preambulo = ARQUIVOS[nome]
        self._caminho(nome).write_text(render_registros(preambulo, registros), encoding="utf-8")

    # ----------------------------------------------------------- alteração
    def registrar_alteracao(self, *, componente: str, operacao: str, versao_anterior: str,
                            versao_nova: str, diferenca: str, motivo: str, responsavel: str,
                            autorizacao: str, hoje: date, beneficio: str = NAO_INFORMADO,
                            risco: str = NAO_INFORMADO, custo: str = "não medido",
                            teste: str = NAO_INFORMADO, reversao: str = NAO_INFORMADO) -> Registro:
        return self.acrescentar("alteracoes", {
            "componente": componente, "operacao": operacao, "versao_anterior": versao_anterior,
            "versao_proposta": versao_nova, "diferenca": diferenca, "motivo": motivo or NAO_INFORMADO,
            "beneficio": beneficio, "risco": risco, "custo": custo, "teste": teste,
            "plano_de_reversao": reversao, "responsavel": responsavel, "autorizacao": autorizacao,
            "data": hoje.isoformat(),
        })

    def alteracoes_desde(self, ultimo_id: str | None) -> list[Registro]:
        registros = self.ler("alteracoes")
        if not ultimo_id:
            return registros
        vistos = True
        saida = []
        for registro in registros:
            if not vistos:
                saida.append(registro)
            if registro.id == ultimo_id:
                vistos = False
        return saida if not vistos else registros

    # -------------------------------------------------------------- versões
    def guardar_versao(self, componente: str, numero: int, arquivos: list[Path]) -> Path:
        destino = self.pasta_versoes / componente / f"v{numero:03d}"
        if destino.exists():
            return destino
        destino.mkdir(parents=True)
        for arquivo in arquivos:
            if arquivo.is_file():
                shutil.copyfile(arquivo, destino / arquivo.name)
        return destino

    def versoes(self, componente: str) -> list[Path]:
        pasta = self.pasta_versoes / componente
        if not pasta.is_dir():
            return []
        return sorted(p for p in pasta.iterdir() if p.is_dir() and p.name.startswith("v"))

    def restaurar_versao(self, componente: str, numero: int, destino: Path) -> list[Path]:
        origem = self.pasta_versoes / componente / f"v{numero:03d}"
        if not origem.is_dir():
            raise FileNotFoundError(f"não existe a versão v{numero:03d} de {componente}")
        restaurados = []
        for arquivo in sorted(origem.iterdir()):
            shutil.copyfile(arquivo, destino / arquivo.name)
            restaurados.append(destino / arquivo.name)
        return restaurados

    # --------------------------------------------------------------- custos
    def custo_de(self, componente: str) -> str:
        total = 0.0
        unidade = ""
        encontrados = 0
        for registro in self.ler("custos"):
            if registro.get("componente") != componente:
                continue
            try:
                total += float(registro.get("valor", "0").replace(",", "."))
            except ValueError:
                continue
            unidade = registro.get("unidade", unidade)
            encontrados += 1
        if not encontrados:
            return "CONSUMO NÃO MEDIDO"
        return f"{total:g} {unidade} (medido em {encontrados} registro(s))".strip()
