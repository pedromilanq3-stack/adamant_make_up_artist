#!/bin/sh
# Clique duplo (macOS/Linux): o acaso age sobre NEX e os arquivos das salas são regenerados.
cd "$(dirname "$0")/../.." || exit 1
python3 -m nucleo mente acaso NEX --quantos 2
python3 -m nucleo empacotar >/dev/null
python3 -m nucleo mente estado NEX
