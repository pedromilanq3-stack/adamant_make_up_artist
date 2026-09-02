"""Gera o arquivo único ``cerebro.pyz`` (executável Python de um arquivo só).

    python ferramentas/empacotar_cerebro.py            # escreve cerebro.pyz na raiz
    python ferramentas/empacotar_cerebro.py saida.pyz  # outro caminho

O ``.pyz`` usa apenas a biblioteca padrão (``zipapp``) e roda com
``python cerebro.pyz`` em qualquer Python 3.11 ou mais novo.
"""

from __future__ import annotations

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


def main(argv: list[str]) -> None:
    target = Path(argv[0]) if argv else ROOT / "cerebro.pyz"
    build(target)
    print(f"Gerado {target} ({target.stat().st_size // 1024} KB). Execute com: python {target.name}")


if __name__ == "__main__":
    main(sys.argv[1:])
