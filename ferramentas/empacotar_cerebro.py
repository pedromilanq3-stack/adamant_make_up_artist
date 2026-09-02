"""Gera os arquivos únicos ``cerebro.pyz`` e ``cerebro_android.py``.

    python ferramentas/empacotar_cerebro.py            # escreve os dois na raiz
    python ferramentas/empacotar_cerebro.py saida.pyz  # só o .pyz, em outro caminho

O ``.pyz`` usa apenas a biblioteca padrão (``zipapp``) e roda com
``python cerebro.pyz`` em qualquer Python 3.11 ou mais novo.

O ``cerebro_android.py`` é um ``.py`` comum que carrega o programa inteiro
(o mesmo zip, em base64) e abre o chat. Serve para o Pydroid 3 no Android,
onde só é preciso abrir o arquivo e tocar em executar.
"""

from __future__ import annotations

import base64
import shutil
import sys
import tempfile
import zipapp
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "cerebro"

LAUNCHER = '''"""Ponto de entrada do cerebro.pyz."""
from cerebro.__main__ import main

main()
'''


def build(target: Path) -> Path:
    with tempfile.TemporaryDirectory() as directory:
        staging = Path(directory) / "app"
        shutil.copytree(PACKAGE, staging / "cerebro", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (staging / "__main__.py").write_text(LAUNCHER, encoding="utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        zipapp.create_archive(staging, target, interpreter="/usr/bin/env python3", compressed=True)
    return target


ANDROID_TEMPLATE = '''"""Cérebro para Android (Pydroid 3): abra este arquivo e toque em executar.

Depois, no navegador do próprio celular, acesse http://127.0.0.1:8766
Mantenha o Pydroid aberto enquanto conversa. Os cérebros ficam gravados na
pasta do Pydroid; para parar, toque no botão de parar do Pydroid.

Este arquivo carrega o programa inteiro (gerado por
ferramentas/empacotar_cerebro.py); não precisa de mais nada além do Python 3.11+.
"""

import base64
import os
import sys
import tempfile

PORTA = 8766
PACOTE = (
{payload}
)


def preparar() -> str:
    pasta = os.path.join(tempfile.gettempdir(), "cerebro_app")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, "cerebro.pyz")
    dados = base64.b64decode("".join(PACOTE))
    try:
        atual = open(caminho, "rb").read()
    except OSError:
        atual = b""
    if atual != dados:
        with open(caminho, "wb") as arquivo:
            arquivo.write(dados)
    return caminho


def main() -> None:
    if sys.version_info < (3, 11):
        print("Este programa precisa do Python 3.11 ou mais novo. Atualize o Pydroid 3 ou o Python.")
        return
    sys.path.insert(0, preparar())
    if not os.environ.get("CEREBRO_DIR"):
        os.environ["CEREBRO_DIR"] = os.path.join(os.path.expanduser("~"), "cerebro_dados")
    from cerebro.__main__ import main as cerebro_main

    argumentos = sys.argv[1:]
    if not argumentos:
        argumentos = ["web", "--porta", str(PORTA), "--abrir"]
        print("Abra no navegador: http://127.0.0.1:%d  (mantenha este app aberto)" % PORTA)
    cerebro_main(argumentos)


if __name__ == "__main__":
    main()
'''


def build_android(pyz: Path, target: Path) -> Path:
    encoded = base64.b64encode(pyz.read_bytes()).decode("ascii")
    lines = [f'    "{encoded[i:i + 100]}"' for i in range(0, len(encoded), 100)]
    target.write_text(ANDROID_TEMPLATE.replace("{payload}", "\n".join(lines)), encoding="utf-8")
    return target


def main(argv: list[str]) -> None:
    if argv:
        target = build(Path(argv[0]))
        print(f"Gerado {target} ({target.stat().st_size // 1024} KB). Execute com: python {target.name}")
        return
    pyz = build(ROOT / "cerebro.pyz")
    android = build_android(pyz, ROOT / "cerebro_android.py")
    print(f"Gerado {pyz.name} ({pyz.stat().st_size // 1024} KB) e {android.name} ({android.stat().st_size // 1024} KB).")


if __name__ == "__main__":
    main(sys.argv[1:])
