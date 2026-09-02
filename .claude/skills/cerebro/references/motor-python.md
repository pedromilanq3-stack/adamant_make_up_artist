# Modo motor (opcional)

Se o repositório com o pacote `cerebro/` estiver disponível e houver Python 3.11+, o
motor em código substitui as contas mentais, com mais precisão e acaso de verdade.

- Criar: `python -m cerebro criar --nome "Nome" --descricao "..." --arquivo cerebros/nome.json [--genero f]`
- A cada mensagem: `python -m cerebro turno --arquivo cerebros/nome.json --mensagem "<mensagem>" --resposta-anterior "<sua última resposta>"`
  (na primeira mensagem, omita `--resposta-anterior`). O comando imprime o bloco
  `<cerebro>`; leia-o e responda como personagem.
- `python -m cerebro estado --arquivo ...`, `python -m cerebro acaso --arquivo ...`.
- Salvar: `git add cerebros/ && git commit`.

Não misture os dois modos no mesmo cérebro: a ficha em texto e o JSON do motor são
estados diferentes.
