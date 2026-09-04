#!/bin/sh
# Clique duplo (macOS/Linux): o acaso age sobre BATMAN e os arquivos das salas são regenerados.
cd "$(dirname "$0")/../.." || exit 1
python3 -m nucleo mente acaso BATMAN --quantos 2
python3 -m nucleo empacotar >/dev/null
python3 -m nucleo mente estado BATMAN
