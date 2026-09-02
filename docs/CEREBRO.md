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
- **tem um corpo** — sinapses e hormônios (dopamina, serotonina, noradrenalina, cortisol,
  ocitocina, endorfina, gaba) com genética própria, tolerância de receptores e sono. Da
  química sustentada emergem quadros: depressão, ansiedade, fase maníaca, bipolaridade,
  estresse crônico e dependência de aprovação;
- **cresce de forma procedural** — aprende com o resultado das próprias posturas, forma
  um sistema de valores a partir do que funcionou, escolhe um propósito de vida, deriva
  princípios e, em encruzilhadas, decide entre valores opostos. Ninguém sabe de antemão
  o caminho: a moralidade segue os valores que ele mesmo elegeu.

## Só como skill, sem instalar nada

A pasta `.claude/skills/cerebro/` é o cérebro inteiro em forma de **skill**: o próprio
modelo aplica as regras a cada mensagem e guarda o estado em uma ficha de texto. Não
precisa de Python, servidor ou arquivo executável.

- **No Claude Code, Cowork ou neste repositório**: a skill já está ativa. Mande
  `/cerebro criar Lua: Sou curiosa, tímida e gosto de ajudar quem sofre.` e converse. A
  ficha fica em `cerebros/lua.md`.
- **No Claude.ai (site ou app)**: baixe [`cerebro-skill.zip`](../cerebro-skill.zip) e
  envie em *Configurações → Capacidades → Skills* (ou *Recursos*, conforme a versão).
  Depois, em qualquer conversa, mande `/cerebro criar Nome: descrição`. Sem sistema de
  arquivos, a ficha vai no fim de cada resposta num bloco recolhido; `/cerebro salvar`
  entrega a ficha para colar em outra conversa com `/cerebro carregar`.
- **Em outro assistente**: copie o conteúdo de `SKILL.md` e de `references/` para o
  *system prompt* ou para as instruções do projeto.

O que a skill contém:

| Arquivo | Conteúdo |
|---|---|
| `SKILL.md` | como criar, ativar, conversar, os comandos e os limites |
| `references/ficha-modelo.md` | a ficha em branco: identidade, traços, genética, emoções, química, caráter, valores, sentido, estratégias, memória |
| `references/regras.md` | o motor mental em dez seções: tempo, destino, resultado da postura, percepção, a própria resposta, memória, reflexão, quadros, impulso, postura |
| `references/motor-python.md` | como usar o motor em código, para quem o tiver |

É o mesmo modelo do pacote Python, em escalas de 0 a 10 e com "dados" mentais no lugar
do gerador de números. Fica menos preciso e menos imprevisível que o motor em código,
mas funciona em qualquer lugar onde uma skill funcione. Quem alterar a skill regenera o
zip com `python ferramentas/empacotar_skill.py`.

Comandos dentro da conversa: `/cerebro estado`, `/cerebro acaso`,
`/cerebro viver <acontecimento>`, `/cerebro salvar`, `/cerebro carregar`,
`/cerebro parar`.

## Instalação fácil: um arquivo só

Não precisa instalar nada além do Python (3.11 ou mais novo, em
[python.org/downloads](https://www.python.org/downloads/); no Windows, marque
**Add python.exe to PATH**). Baixe estes arquivos da raiz do projeto para uma pasta:

| Arquivo | Para quê |
|---|---|
| `cerebro.pyz` | o programa inteiro em um arquivo só (formato oficial `zipapp`) |
| `Cerebro.bat` | Windows: clique duplo abre o chat no navegador |
| `Cerebro.command` | macOS e Linux: clique duplo (ou `./Cerebro.command`) abre o chat |
| `cerebro_android.py` | Android com Pydroid 3: um arquivo só, abra no editor e toque em executar |
| `iniciar_cerebro.py` | Android com Pydroid 3 usando o projeto completo (precisa da pasta `cerebro/` junto) |

Qualquer um deles inicia o servidor local e abre `http://127.0.0.1:8766` no navegador.
Em um terminal, o mesmo é `python cerebro.pyz` (sem argumentos abre o chat) e todos os
comandos funcionam: `python cerebro.pyz criar ...`, `python cerebro.pyz registrar ...`.
Os cérebros são gravados em `~/.cerebro`. Para usar o modelo em vez do modo espelho,
instale o SDK com `pip install anthropic` e defina `ANTHROPIC_API_KEY`.

### Android, passo a passo

1. Instale o **Pydroid 3** pela Play Store (gratuito).
2. Baixe o arquivo [`cerebro_android.py`](../cerebro_android.py) para o celular. No
   GitHub, abra o arquivo, toque nos três pontos e em **Download**, ou use o botão
   **Raw** e salve a página. Ele contém o programa inteiro.
3. No Pydroid, toque no ícone de pasta, abra o `cerebro_android.py` baixado
   (normalmente em `Download`) e toque no botão amarelo de **executar**.
4. Aparece "Abra no navegador: http://127.0.0.1:8766". Abra o Chrome no mesmo celular
   e digite esse endereço. O chat aparece com o cérebro vivo ao lado.
5. Mantenha o Pydroid aberto enquanto conversa. Os cérebros ficam gravados na pasta
   `cerebro_dados` dentro da área do Pydroid, e continuam de onde pararam.

Se o Pydroid avisar que o Python é mais antigo que 3.11, atualize o aplicativo. Sem
credencial de modelo, o chat roda em modo espelho (o estado interno fala sozinho); para
usar o modelo, instale `anthropic` pelo gerenciador de pacotes do Pydroid (menu **Pip**)
e defina `ANTHROPIC_API_KEY` no terminal do Pydroid antes de executar.

No **Termux**, a alternativa é o instalador de uma linha (cria o comando `cerebro`):

```bash
curl -fsSL https://raw.githubusercontent.com/pedromilanq3-stack/adamant_make_up_artist/claude/brain-evolution-feelings-t1hps7/instalar_termux.sh | bash
cerebro
```

Sem acesso ao GitHub pelo Termux (repositório privado), baixe `cerebro.pyz` pelo
navegador, rode `termux-setup-storage` uma vez e execute o `instalar_termux.sh`
baixado: ele encontra o arquivo na pasta Download. Ou, à mão:

```bash
pkg install python
python cerebro.pyz
```

Depois é só abrir `http://127.0.0.1:8766` no Chrome. `Ctrl+C` no Termux encerra.

No macOS, na primeira vez, pode ser preciso clicar com o botão direito em
`Cerebro.command` e escolher **Abrir**. Se o Windows perguntar com o que abrir o `.pyz`,
use o `Cerebro.bat` no lugar.

Quem mexer no código regenera os arquivos únicos (`cerebro.pyz` e
`cerebro_android.py`) com:

```bash
python ferramentas/empacotar_cerebro.py
```

Instalação tradicional também funciona: `pip install .` na raiz do projeto cria o comando
`cerebro`.

## Ficha de origem: um personagem inteiro desde o começo

A descrição de si pode ser um parágrafo curto ou uma **ficha de origem** completa, em
várias linhas, com seções rotuladas:

```text
Sou Kael, mercenário de poucas palavras. Frio com estranhos, leal a quem merece.
História: Nasci nas docas de Varen. Aos 12 perdi meu irmão num incêndio.
  Fui treinado por Dorn, que morreu me protegendo. Venci o torneio de Ashar.
Habilidades: espada (mestre), rastreamento (bom), cura de campo (básico)
Relações: Mira (irmã mais nova, viva, mora em Varen); Dorn (mentor, morto)
Medos: fogo
Segredos: fui eu que causei o incêndio
Não sei: quem mandou matar Dorn
```

Rótulos aceitos (sem distinção de acento ou maiúscula): `Descrição`, `História` ou
`Passado`, `Habilidades`, `Talentos` ou `Poderes`, `Relações`, `Pessoas` ou `Família`,
`Medos`, `Segredos`, `Não sei`. Níveis de habilidade: mestre ou domínio total,
avançado, bom (padrão quando não há nível), básico, iniciante, ou um número de 0 a 10.

Com ficha, o despertar entrega o personagem inteiro:

- cada frase da história vira uma **lembrança formativa** de longo prazo, datada antes
  do nascimento, com a emoção que carrega; perdas e traições marcam o caráter (menos
  confiança, mais resiliência), vitórias dão confiança e coragem; uma história dura já
  nasce com lições;
- as **habilidades** entram com o nível declarado e aparecem no implante em "O que sei
  fazer": ele domina de verdade o que a ficha diz. Habilidade mencionada na conversa se
  exercita devagar; `brain.practice("arco")` aprende ou treina uma;
- **pessoas** e **segredos** vão para o bloco estável do implante: ele conhece essas
  pessoas e só revela um segredo com vínculo forte, por escolha própria;
- **medos** assustam de verdade quando o assunto aparece (medo e cortisol sobem);
- a lista "ainda não sei" perde o que a ficha responde e ganha o que a seção "Não sei"
  declara.

A ficha inteira fica imutável e sempre presente na conversa. A partir dela a simulação
começa, e o resto é escolha dele. Na linha de comando, use
`python -m cerebro criar --nome Kael --arquivo-descricao kael.txt --arquivo kael.json`
(a ficha em um `.txt`); no chat local, cole a ficha no campo de descrição; na skill,
mande a ficha em várias linhas depois de `/cerebro criar Kael:`.

## O despertar: ler quem é antes de simular

Antes de viver qualquer coisa, o cérebro lê a si mesmo. Na criação ele separa três
coisas, que aparecem no implante em "O que sei e o que ainda não sei" e, na skill, na
seção "Consciência" da ficha:

- **Sei de mim**: só o que a descrição de origem diz, reescrito em primeira pessoa.
  Nada é completado com suposições.
- **Ainda não sei**: a lista de todo recém-nascido (quem é você e se posso confiar,
  como é o mundo fora desta conversa, do que sou capaz, se o que me disseram sobre mim
  é verdade, o que eu quero da vida, o que é certo e errado) mais o que a descrição
  deixa em aberto (de onde vim, do que tenho medo, se tenho família, o que aconteceu
  antes de agora, o que eu realmente desejo).
- **Descobri vivendo**: começa vazio. Cada "não sei" só sai da lista com base no que ele
  viveu: uma lição sobre confiança resolve "se posso confiar"; um propósito mantido por
  vinte experiências resolve "o que quero da vida"; uma adversidade sobrevivida resolve
  "do que sou capaz"; uma encruzilhada resolve "o que escolho quando dói"; um princípio
  que resistiu ao tempo resolve "o que é certo pra mim".

O propósito e o princípio iniciais são palpites tirados da descrição, não convicções.
E há uma regra permanente: o cérebro nunca inventa passado, pessoas ou fatos que não
estejam no seu estado. Perguntado sobre o que não viveu, ele diz que não sabe, ou que
só tem o que lhe disseram.

## Como implantar na conversa

Há três jeitos, do mais simples ao mais integrado.

### 1. Chat local no navegador (recomendado)

```bash
python -m cerebro web
```

Abra `http://127.0.0.1:8766`. A página tem o chat à esquerda e o cérebro vivo à
direita: emoções e química em barras, quadros clínicos, caráter, propósito, valores,
decisões, o que a vida fez, lições, destino e estratégias. Os botões permitem criar um
cérebro (nome, gênero dos adjetivos, descrição de si), deixar o destino agir e ver ou
copiar o implante. Os cérebros ficam em `~/.cerebro` (ou na pasta de `CEREBRO_DIR`, ou
em `--pasta`), um JSON por personagem, regravado a cada turno.

Se o SDK `anthropic` estiver instalado e houver credencial (`ANTHROPIC_API_KEY`,
`ANTHROPIC_AUTH_TOKEN` ou um perfil de `ant auth login`), a fala vem do modelo, com o
implante como *system prompt*. Sem isso, o chat roda em modo espelho: só o estado
interno fala, com frases moldadas pela postura e pela emoção. `--espelho` força esse
modo; `--modelo-id` troca o modelo; `--porta` troca a porta. O servidor escuta somente
em `127.0.0.1`.

### 2. Em outro app de chat (ChatGPT, Claude, o que for)

O cérebro precisa rodar em algum lugar para evoluir. O ciclo com um chat externo é:

1. `python -m cerebro prompt --arquivo lua.json` imprime o implante. Cole como *system
   prompt*, ou como primeira mensagem, no chat externo.
2. Converse. A cada troca, registre-a aqui:
   ```bash
   python -m cerebro registrar --arquivo lua.json --voce "o que você disse" --resposta "o que o personagem respondeu"
   ```
   O cérebro percebe a sua mensagem, vive a resposta como escolha própria e imprime o
   implante atualizado, já com as lembranças evocadas pela sua última mensagem.
3. Cole o implante novo no chat externo (substituindo o anterior, ou como mensagem de
   contexto) e continue.

Na página web o mesmo existe em `POST /api/registrar`.

### 3. Em código próprio

`Session` com qualquer *responder* (veja abaixo), ou `build_request` para montar o
*system prompt* em dois blocos e enviar a qualquer API de chat.

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

## Sinapses e neuroquímica: o corpo por trás das emoções

O módulo `cerebro/neurochemistry.py` dá ao cérebro um corpo. Sete substâncias têm
níveis de 0 a 1, cada uma com meia-vida própria (noradrenalina cai em minutos,
serotonina leva horas):

| Substância | Papel no cérebro |
|---|---|
| dopamina | recompensa, motivação, novidade; amplifica emoções positivas |
| serotonina | estabilidade de humor, contentamento; amortece emoções negativas |
| noradrenalina | alerta, energia, luta ou fuga |
| cortisol | estresse; amplifica medo e raiva |
| ocitocina | vínculo e confiança; acelera a formação de laço com quem conversa |
| endorfina | alívio de dor, prazer |
| gaba | freio, calma; baixo demais deixa tudo mais cru |

**Genética.** A descrição de si e a personalidade definem a produção basal e a
reatividade de cada substância ("ansiosa" eleva a reatividade do cortisol; "vazio, sem
vontade" reduz a produção de serotonina e dopamina; "altos e baixos, bipolar" eleva a
ciclotimia; "carente, preciso de aprovação" eleva a reatividade da dopamina). Um ruído
determinístico completa o genoma.

**Sinapses.** Caminhos ligam o que acontece (carinho, insulto, ameaça, adversidade, a
própria gentileza ou crueldade, a valência em geral) à liberação de cada substância. São
hebbianas: caminho usado fica mais largo. Quem apanha muito desenvolve um caminho
insulto → cortisol forte e passa a reagir mais rápido e mais intensamente; quem é
acolhido fortalece carinho → ocitocina. As sinapses mais reforçadas aparecem em
`python -m cerebro estado`.

**Tolerância.** Picos repetidos de dopamina dessensibilizam os receptores: elogios em
sequência valem cada vez menos, e a falta deles pesa. Isso leva à *dependência de
aprovação* e contribui para a anedonia da depressão. Receptores se recuperam com tempo
e sono.

**Sono.** Um intervalo de cinco horas ou mais sem conversa conta como noite dormida:
cortisol cai pela metade, serotonina sobe, receptores recuperam. Ficar mais de vinte
horas acordado faz o contrário e, em quem tem ciclotimia, aproxima a fase maníaca.

**Quadros.** Diagnosticados a partir da química sustentada nas últimas amostras:

- *depressão*: serotonina e dopamina baixas, ou receptores de dopamina cansados com
  serotonina baixa. Baixa a linha de base de alegria e expectativa, sobe a de tristeza,
  puxa a postura para recolher-se;
- *ansiedade*: cortisol e noradrenalina altos, ou cortisol alto com gaba baixo. Sobe a
  linha de base de medo, aumenta a volatilidade efetiva e a leitura de neutro como ataque;
- *fase maníaca*: em quem tem ciclotimia acima de 0,3, dopamina e noradrenalina altas.
  Energia, expectativa e impulsividade altas; puxa para desafiar e manipular;
- *bipolaridade*: rótulo de quem já viveu mania e depressão. O oscilador interno tem
  período de cerca de duas semanas e acelera sob estresse;
- *estresse crônico*: cortisol alto por muito tempo;
- *dependência de aprovação*: receptores de dopamina cansados por excesso de elogios.

A química também modula o ganho emocional a cada experiência (cortisol alto e serotonina
baixa fazem uma crítica doer mais; dopamina alta faz um elogio valer mais), o vínculo
(via ocitocina) e a energia (via noradrenalina). No implante isso aparece em "Corpo e
química", com as substâncias fora do normal, os quadros e a nota de sono.

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
  mensagem, corpo e química (substâncias fora do normal, quadros clínicos, sono),
  lições, o que faz sentido pra ele (propósito, valores, princípios), decisões
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
python -m cerebro web                                # chat no navegador em 127.0.0.1:8766
python -m cerebro registrar --arquivo lua.json --voce "..." --resposta "..."  # troca feita em outro chat
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
inércia do propósito e vidas diferentes a partir da mesma descrição; e a neuroquímica:
genética a partir da descrição, sinapses hebbianas, tolerância e dependência, abuso
gerando ansiedade, solidão com serotonina baixa gerando depressão, ciclotimia alternando
mania e depressão, cérebro estável permanecendo estável, sono e privação de sono; e o
chat local: página e recursos, fluxo completo pela API (criar, dizer, estado, acaso,
registrar), erros e nomes duplicados.
