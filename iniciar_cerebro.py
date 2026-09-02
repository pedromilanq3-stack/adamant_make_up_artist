"""Inicializador do Cérebro para editores como o Pydroid 3 (Android).

Abra este arquivo no Pydroid, toque em executar e acesse
http://127.0.0.1:8766 no navegador do mesmo aparelho. Não escreva
``python -m cerebro`` dentro do editor: isso é um comando de terminal.
"""

from cerebro.web import serve


if __name__ == "__main__":
    serve(open_browser=True)
