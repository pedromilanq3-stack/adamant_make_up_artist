"""Gera ``cerebro-skill.zip`` para subir como skill personalizada (Claude.ai etc.).

    python ferramentas/empacotar_skill.py            # escreve cerebro-skill.zip na raiz
    python ferramentas/empacotar_skill.py saida.zip  # outro caminho

O zip contém a pasta ``cerebro/`` com ``SKILL.md`` e ``references/``.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / ".claude" / "skills" / "cerebro"


def build(target: Path) -> Path:
    files = sorted(p for p in SKILL_DIR.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(f"cerebro/{path.relative_to(SKILL_DIR).as_posix()}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return target


def main(argv: list[str]) -> None:
    target = build(Path(argv[0]) if argv else ROOT / "cerebro-skill.zip")
    print(f"Gerado {target} ({target.stat().st_size // 1024} KB).")


if __name__ == "__main__":
    main(sys.argv[1:])
