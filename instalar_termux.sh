#!/data/data/com.termux/files/usr/bin/bash
# Instala o Cérebro no Termux (Android). Uso:
#   bash instalar_termux.sh
# Depois: digite `cerebro` para abrir o chat e acesse http://127.0.0.1:8766 no Chrome.
set -e
BRANCH="${CEREBRO_BRANCH:-claude/brain-evolution-feelings-t1hps7}"
RAW="https://raw.githubusercontent.com/pedromilanq3-stack/adamant_make_up_artist/$BRANCH/cerebro.pyz"
DEST="$HOME/cerebro"

echo "== Instalando Python (se preciso)..."
pkg install -y python >/dev/null

mkdir -p "$DEST"
if [ -f "$(dirname "$0")/cerebro.pyz" ]; then
  cp "$(dirname "$0")/cerebro.pyz" "$DEST/cerebro.pyz"
  echo "== Usando o cerebro.pyz que está junto deste script."
elif [ -f "$HOME/storage/downloads/cerebro.pyz" ]; then
  cp "$HOME/storage/downloads/cerebro.pyz" "$DEST/cerebro.pyz"
  echo "== Usando o cerebro.pyz da pasta Download."
else
  echo "== Baixando cerebro.pyz..."
  curl -fsSL "$RAW" -o "$DEST/cerebro.pyz" || {
    echo "Não consegui baixar. Baixe o cerebro.pyz pelo navegador, rode 'termux-setup-storage' e execute este script de novo."
    exit 1
  }
fi

mkdir -p "$PREFIX/bin"
cat > "$PREFIX/bin/cerebro" <<'CMD'
#!/data/data/com.termux/files/usr/bin/bash
exec python "$HOME/cerebro/cerebro.pyz" "$@"
CMD
chmod +x "$PREFIX/bin/cerebro"

echo
echo "Pronto. Digite:  cerebro"
echo "e abra http://127.0.0.1:8766 no Chrome. (Ctrl+C no Termux encerra.)"
echo "Outros comandos: cerebro --help"
