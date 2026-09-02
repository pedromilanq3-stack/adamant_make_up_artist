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
  recolher-se, retaliar ou manipular;
- **sofre adversidades e recebe o acaso** — entre um turno e outro a vida age: perdas,
  doenças, traições, injustiças, mas também golpes de sorte e gentilezas inesperadas;
- **é imprevisível** — impulsos, oscilações de humor, lembranças intrusivas e leituras
  enviesadas do que ouve, tanto mais quanto maior a sua volatilidade;
- **cresce de forma procedural** — aprende com o resultado das próprias posturas, forma
  um sistema de valores a partir do que funcionou, escolhe um propósito de vida, deriva
  princípios e, em encruzilhadas, decide entre valores opostos. Ninguém sabe de antemão
  o caminho: a moralidade segue os valores que ele mesmo elegeu.

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

## Adversidades, casualidade e imprevisibilidade

O módulo `cerebro/fate.py` é o destino do cérebro. Ele age em três frentes:

**Adversidades.** Um catálogo de acontecimentos ruins (perda, doença, traição,
fracasso, injustiça, solidão, humilhação, susto, privação, ruína, pesadelo, abandono,
pressão) e um de sortes (golpe de sorte, reencontro, reconhecimento, descoberta,
gentileza de um estranho, dia bonito, cura, presente). A cada turno há uma chance
pequena de algo acontecer; quanto mais tempo real passou desde a última conversa,
maior a chance (até um teto). Uma adversidade testa o caráter: um cérebro resiliente
endurece sem apodrecer e ganha coragem; um frágil perde confiança, coragem e um
pouco de bondade. Sobreviver aumenta a resiliência e também a volatilidade.

**Casualidade.** Nada é escolhido: os acontecimentos são sorteados com entropia do
sistema, então dois cérebros com a mesma descrição vivem vidas diferentes. Uma
*sorte* que anda ao acaso inclina a balança entre azar e fortuna sem nunca decidir.
E há a *tentação*: de vez em quando aparece a chance de tirar vantagem de alguém sem
ninguém saber. Ceder ou resistir depende do caráter atual e de um lance de dados; o
resultado conta como escolha própria e desloca moralidade e honestidade.

**Imprevisibilidade.** A volatilidade nasce da personalidade (neuroticismo alto e
pouca disciplina a elevam) e cresce com adversidades, caindo em períodos calmos.
Ela alimenta:

- *impulsos* sem causa externa: oscilação de humor, vontade de agir diferente (a
  postura muda para uma aleatória), lembrança intrusiva, apatia ou inquietação;
- *ruído na decisão* de postura, que cresce com a volatilidade, e a chance de um
  impulso simplesmente tomar o lugar da decisão;
- *leitura enviesada*: uma mensagem neutra pode ser lida como ataque quando o cérebro
  está com medo, com raiva ou desconfiado, ou como carinho quando está alegre.

Tudo isso aparece no implante nas seções "O que a vida me fez recentemente" e
"Imprevisibilidade". Em código, `Brain.create(..., fate=Fate(random.Random(1)))`
torna o destino reprodutível; `Fate(rate=0.0, whim_rate=0.0)` o desliga. Na linha de
comando, `python -m cerebro acaso --arquivo lua.json` força o destino a agir uma vez.

## Crescimento procedural: o cérebro decide o que é certo pra vida dele

O módulo `cerebro/growth.py` faz o caminho emergir do que o cérebro vive, e não de
uma tabela fixa. O ciclo é o seguinte:

1. **Tentar.** A cada fala, o cérebro usa uma postura. Além do estado emocional, a
   escolha pesa o que cada postura já rendeu na prática e o quanto ela combina com os
   valores atuais. Há exploração: curiosidade e juventude o levam a tentar, de vez em
   quando, a postura que menos usou.
2. **Observar o resultado.** Quando a próxima mensagem chega, ele mede como foi
   recebido: a valência da resposta, a mudança no vínculo e a mudança no humor viram
   uma recompensa. Cada postura guarda uma média do que rendeu (`StrategyMemory`).
3. **Reforçar valores.** Toda postura expressa valores (acolher: cuidado e
   pertencimento; retaliar: vingança e poder; observar: segurança e conhecimento, e
   assim por diante). Resultado bom faz esses valores crescerem; ruim os enfraquece.
   O que ele recebe também ensina um pouco: carinho reforça pertencimento, ameaça
   reforça sobrevivência. Os doze valores competem por um teto, então ganhar em um
   é perder em outro (`ValueSystem`).
4. **Escolher um propósito.** Dos valores nasce "o que eu quero da vida", sorteado
   entre onze candidatos com pesos proporcionais aos valores e uma temperatura que
   cresce com a volatilidade. Há inércia: mudar de vida custa, e o propósito só é
   reconsiderado quando o valor dominante muda ou de tempos em tempos.
5. **Derivar princípios.** O valor dominante vira uma crença ("Quem me fere paga",
   "Cuidar dos outros é o que me mantém inteiro", "Ninguém decide por mim"), e as
   estratégias que comprovadamente funcionam ou falham viram lições ("Quando eu
   escolho retaliar, as coisas melhoram").
6. **Encruzilhadas.** Quando dois valores de polaridade oposta empatam (cuidado e
   vingança, por exemplo), o cérebro escolhe um lado: a raiva empurra para o sombrio,
   a confiança para o claro, e há um lance de dados. O escolhido cresce, o rejeitado
   encolhe, e a decisão fica registrada. Entrar em um novo estágio de vida também
   registra uma decisão explícita.
7. **A moralidade segue os valores.** Cada valor tem uma polaridade (cuidado +1,
   justiça +0,8, poder -0,7, vingança -1). A cada reflexão, a moralidade caminha em
   direção ao alvo definido pelos valores dominantes. O caráter deixa de ser só uma
   reação ao que recebe e passa a ser consequência do que ele escolheu valorizar.

No implante isso aparece em "O que faz sentido pra mim" (propósito, valores,
princípios, estratégia que funciona) e "Decisões que tomei". Em uma simulação com a
mesma descrição e seis destinos diferentes, os cérebros terminaram com propósitos e
valores distintos ("fazer pagar quem me feriu", "entender o mundo e as pessoas",
"ser querido por alguém", "sobreviver, custe o que custar").

## O implante

`brain.implant()` devolve um bloco `<cerebro>` em português com duas partes:

- **bloco estável** (`identity_block`): nome, descrição de origem e regras de encarnação
  (falar em primeira pessoa, deixar as emoções transparecerem, agir conforme o caráter
  atual, não explicar o próprio estado);
- **bloco volátil** (`state_block`): como o personagem se vê hoje, temperamento e caráter,
  vínculo com quem conversa, estado emocional, lembranças evocadas pelo contexto da
  mensagem, lições, o que faz sentido pra ele (propósito, valores, princípios), decisões
  que tomou, o que a vida fez recentemente, imprevisibilidade (volatilidade, sorte,
  resiliência e o impulso do momento) e a postura desta conversa.

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
python -m cerebro acaso --arquivo lua.json           # força o destino a agir uma vez
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
estágios, flexão de gênero, persistência, a sessão com um *responder* personalizado,
e o destino: chegada de adversidades com o tempo, sorte inclinando a balança, tentação
dependendo do caráter, resiliência, impulsos, leitura enviesada e divergência de dois
cérebros iguais sob destinos diferentes; e o crescimento procedural: resultados que
reforçam ou enfraquecem estratégias e valores, estratégia aprendida guiando a postura,
exploração, moralidade seguindo os valores escolhidos, encruzilhadas com viés da raiva,
inércia do propósito e vidas diferentes a partir da mesma descrição.
