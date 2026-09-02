#!/bin/bash
# Abre o chat do Cérebro no navegador (macOS e Linux). Requer Python 3.11 ou mais novo.
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
  python3 cerebro.pyz "$@"
else
  echo "Instale o Python 3.11 ou mais novo em https://www.python.org/downloads/"
  read -r -p "Pressione Enter para sair."
fi
