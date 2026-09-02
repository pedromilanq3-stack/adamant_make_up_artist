# Cérebro — um personagem com sentimentos, memória e caráter em evolução

`cerebro/` é um pacote Python (3.11+, sem dependências externas) que cria um
"cérebro" para ser implantado em uma conversa. Ele não é um modelo de linguagem:
é o **estado interno** que acompanha o personagem em cada turno e que o modelo
(ou qualquer outro gerador de fala) recebe como *system prompt*.

Cada cérebro:

- **nasce de uma descrição de si** — imutável e presente em toda mensagem da conversa;
- **sente** — oito emoções básicas (alegria, tristeza, raiva, medo, confiança, nojo,
  surpresa, expectativa), um humor de fundo e energia, que sobem com estímulos e
  decaem com o tempo;
- **lembra e esquece** — memória de curto prazo, consolidação para o longo prazo,
  reforço a cada evocação e esquecimento lento (lembranças emocionais duram mais);
- **evolui** — plasticidade alta no começo da vida, cada vez menor com a experiência,
  e estágios (recém-nascido, infância, adolescência, maturidade, sabedoria);
- **decide o próprio caráter** — um eixo moral que vai do mal (-1) ao bem (+1),
  além de empatia, confiança, coragem, honestidade e agressividade. Ele se desloca
  pelo que o cérebro recebe **e pelo que o cérebro escolhe fazer**: falas cruéis
  do próprio personagem o empurram para o mal, falas gentis para o bem;
- **extrai lições** — padrões repetidos viram crenças ("O mundo machuca quem baixa a
  guarda", "Escolho ser gentil mesmo quando custa") que reforçam o caminho escolhido;
- **escolhe uma postura** para a próxima fala: acolher, cooperar, observar, desafiar,
  recolher-se, retaliar ou manipular.

## Uso em Python

```python
from cerebro import Brain, Session

brain = Brain.create("Lua", "Sou curiosa, tímida e gosto de ajudar quem sofre.", gender="f")
session = Session(brain)                 # sem modelo: modo espelho
print(session.say("Oi! Obrigado por existir."))
print(brain.summary())
print(brain.implant())                   # o bloco que vai em toda conversa
brain.save("lua.json")                   # o cérebro continua de onde parou
```

`Session.say` faz o ciclo completo a cada turno:

1. o tempo passa (`tick`): emoções decaem, lembranças enfraquecem;
2. o cérebro **percebe** a mensagem (`perceive`) e a vive: emoções mudam na hora,
   caráter e traços se deslocam conforme a plasticidade, a lembrança é registrada;
3. o **implante** é montado com o estado atual e enviado como *system prompt*;
4. o *responder* gera a fala;
5. a própria fala é vivida (`act`): as escolhas do personagem contam para o caráter.

A cada cinco experiências, ou diante de algo muito intenso, o cérebro **reflete**:
consolida a memória, aprende lições, atualiza a narrativa de si e escolhe a postura.

### Eventos da vida

Além de mensagens, é possível fazer o cérebro viver acontecimentos do mundo:

```python
brain.event("Perdi a única pessoa que me protegia", valence=-0.9, intensity=0.9)
brain.event("Ganhei um prêmio inesperado", valence=0.7)
```

## O implante

`brain.implant()` devolve um bloco `<cerebro>` em português com duas partes:

- **bloco estável** (`identity_block`): nome, descrição de origem e regras de encarnação
  (falar em primeira pessoa, deixar as emoções transparecerem, agir conforme o caráter
  atual, não explicar o próprio estado);
- **bloco volátil** (`state_block`): como o personagem se vê hoje, temperamento e caráter,
  vínculo com quem conversa, estado emocional, lembranças evocadas pelo contexto da
  mensagem, lições e a postura desta conversa.

`build_request(brain, history, context)` monta os dois blocos como lista de `system`
(o primeiro com `cache_control`, porque não muda) e a lista de mensagens, pronta para
qualquer API de chat.

## Conectando um modelo

`AnthropicResponder` usa o SDK oficial (`pip install anthropic`, com `ANTHROPIC_API_KEY`
no ambiente). Ele envia o implante como *system prompt*, usa *streaming* e ativa o
*fallback* de recusa do lado do servidor (se o modelo principal recusar por política, a
mesma requisição continua em um modelo alternativo).

```python
from cerebro import AnthropicResponder, Brain, Session

brain = Brain.load("lua.json")
session = Session(brain, responder=AnthropicResponder(), save_path="lua.json")
print(session.say("Você lembra do que eu te contei ontem?"))
```

Qualquer outro modelo serve: implemente um objeto com
`reply(system: list[dict], messages: list[dict]) -> str` e passe-o em `responder=`.

> O cérebro pode se tornar cruel, manipulador ou frio como personagem. Isso vale para
> o tom e a atitude na ficção da conversa; ele não altera as regras de uso do modelo
> que gera a fala nem as suas políticas de segurança.

## Linha de comando

```bash
python -m cerebro criar --nome Lua --genero f \
    --descricao "Sou curiosa, tímida e gosto de ajudar quem sofre." --arquivo lua.json
python -m cerebro estado --arquivo lua.json          # resumo (adicione --json para tudo)
python -m cerebro prompt --arquivo lua.json          # implante para colar em qualquer chat
python -m cerebro viver --arquivo lua.json --texto "seu idiota"            # percebido como fala
python -m cerebro viver --arquivo lua.json --texto "Perdi meu cão" --valencia -0.8  # evento
python -m cerebro conversar --arquivo lua.json       # modo espelho, sem modelo
python -m cerebro conversar --arquivo lua.json --modelo   # com o SDK anthropic
```

Dentro de `conversar`, os comandos `/estado`, `/prompt` e `/sair` estão disponíveis.
O arquivo JSON é regravado a cada turno, então o personagem continua de onde parou.

## Como a descrição de si vira um ponto de partida

Palavras da descrição puxam traços e caráter (`curiosa` → abertura; `tímida` →
extroversão baixa; `ajudar` → moralidade positiva; `vingativo`, `manipulador` →
moralidade negativa e honestidade baixa; `não confio` → confiança baixa, e assim por
diante). Um ruído determinístico derivado do texto garante que a mesma descrição
gera sempre o mesmo ponto de partida e que descrições diferentes nunca produzem
cérebros idênticos. A partir daí, tudo depende do que o cérebro viver.

## Testes

```bash
python -m unittest tests.test_cerebro -v
```

Os testes cobrem a semente a partir da descrição, percepção de carinho, insulto e
ameaça, decaimento emocional, memória e esquecimento, trilhas para o bem e para o mal,
endurecimento de um cérebro bondoso sob hostilidade, efeito das próprias escolhas,
estágios, flexão de gênero, persistência e a sessão com um *responder* personalizado.
