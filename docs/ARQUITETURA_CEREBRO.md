# Arquitetura do Cérebro — modularidade e adaptação no mesmo sistema

`docs/CEREBRO.md` conta **o que** o cérebro faz. Este documento conta **como ele é
sustentado por dentro**: quais são as camadas, quem pode escrever no quê, em que
ordem as coisas acontecem, o que segura o sistema em pé e onde ele hoje sangra.

É o documento a ler antes de acrescentar um módulo, mudar uma constante ou tentar
explicar por que um cérebro salvo virou outra pessoa.

## O dilema central

O pedido "um cérebro modular que se adapta conforme as coisas acontecem" junta duas
forças que puxam em direções opostas:

- **modularidade** quer fronteiras estáveis: cada arquivo com uma responsabilidade,
  trocável sem entender os vizinhos;
- **adaptação contínua** quer que tudo influencie tudo: a emoção mexe no caráter, o
  caráter mexe na postura, a postura mexe no vínculo, o vínculo mexe na emoção.

Quando essas duas forças não são conciliadas de propósito, o resultado típico é um
sistema **modular nos arquivos e monolítico no estado**: treze arquivos bonitos e um
objeto central onde todos escrevem. É exatamente o risco que este pacote corre, e a
razão de este documento existir.

A conciliação adotada aqui tem três regras:

1. **Separar por velocidade, não por assunto.** O que muda em minutos, o que muda em
   dezenas de experiências e o que muda em centenas são camadas diferentes, com
   taxas declaradas.
2. **Uma direção de escrita.** Cada módulo é dono de um pedaço do estado. Os outros
   leem à vontade e escrevem só através do dono.
3. **Todo laço de realimentação tem freio explícito.** Nada sobe sem ter por onde
   descer, e todo acumulador tem teto.

## Mapa dos módulos

| Arquivo | Responsabilidade | Estado que possui |
|---|---|---|
| `experience.py` | a unidade do que acontece (`Experience`, imutável) e `clamp` | — (só dados) |
| `perception.py` | interpretar um texto e devolver uma `Experience` (`appraise`) | — (sem estado) |
| `emotions.py` | oito emoções, humor, energia, decaimento | `Emotions` |
| `personality.py` | traços (OCEAN), caráter (moralidade, empatia…), plasticidade | `Traits`, `Character` |
| `memory.py` | curto prazo, consolidação, esquecimento, evocação, lições | `MemoryStore` |
| `neurochemistry.py` | sinapses, sete substâncias, genética, quadros clínicos | `Neurochemistry` |
| `growth.py` | valores, propósito, princípios, encruzilhadas, o que rendeu | `ValueSystem`, `StrategyMemory` |
| `fate.py` | o acaso: adversidades, sortes, tentações, impulsos, viés de leitura | `Fate` (só o gerador) |
| `brain.py` | o ciclo de vida: orquestra tudo acima e monta o implante | `Brain` (o resto) |
| `session.py` | um turno de conversa e a ponte com o gerador de fala | `Session.history` |
| `web.py`, `__main__.py` | chat local e linha de comando | — (interface) |

Os módulos das cinco primeiras linhas **não importam `brain.py`**. Essa é a única
regra de dependência que o pacote respeita hoje sem exceção, e ela é o que impede o
sistema de virar um nó: a hierarquia é `brain → (growth, neuro, memory, personality,
emotions, fate, perception) → experience`.

## O ciclo de um turno

A ordem abaixo **é comportamento**, não detalhe de implementação. Trocar dois passos
de lugar dá outro personagem. Por isso ela está escrita aqui e não só no código.

```
Session.say(texto)                                   session.py:134
├─ 1. brain.tick(agora)                              brain.py:177   o tempo passou
│     ├─ neuro.decay        → substâncias voltam ao basal
│     ├─ neuro.assess       → quadros que emergiram viram lição
│     ├─ emotions.decay     → emoções voltam ao basal
│     ├─ memory.forget      → lembranças fracas somem
│     ├─ bond *= …          → vínculo esfria sozinho
│     ├─ fate.roll_events   → a vida agiu no intervalo → live() de cada evento
│     └─ _whim              → um impulso pode surgir do nada
├─ 2. brain.perceive(texto)                          brain.py:305   o que ele ouviu
│     ├─ appraise           → texto vira Experience
│     ├─ fate.misread       → medo/raiva distorcem a leitura
│     ├─ live(experiência)  → ver abaixo
│     └─ guarda acting_stance, bond_before, mood_before  (para medir o resultado)
├─ 3. build_request                                  session.py:35  identidade + estado viram system prompt
├─ 4. responder.reply                                 o modelo (ou o espelho) fala
└─ 5. brain.act(resposta)                            brain.py:332   a própria fala é experiência
      └─ live(experiência com source="self")
```

E `live()` (`brain.py:226`), o coração, na ordem em que aplica:

```
neuro.release        → química primeiro: ela modula tudo que vem depois
emotions.apply       → com ganho de neuroticismo/extroversão × modulação química
character.shift      → amortecido por amabilidade, testado por adversidade
traits.shift         → devagar, sempre × plasticidade
values.reinforce     → as tags do que aconteceu reforçam valores
memory.record        → vira lembrança com a emoção sentida
bond                 → só quando a fonte é o interlocutor
reflect() OU decide_stance()   → a cada 5 experiências, ou se a experiência foi pesada
```

`reflect()` (`brain.py:355`) consolida memória, extrai lições, chama `_grow()`
(`brain.py:410` — encruzilhadas, propósito, princípios, moralidade seguindo os
valores) e escolhe a postura. É o único ponto do sistema onde o cérebro muda de
**direção** em vez de mudar de **grau**.

## As camadas, por velocidade

Esta é a espinha da arquitetura. Um sistema adaptativo sem separação de velocidades
não tem personalidade: ou ele oscila com o último estímulo, ou ele congela.

| Camada | O que é | Velocidade | Onde |
|---|---|---|---|
| **Invariante** | nome, descrição de si, nascimento, `seed`, genética | **nunca muda** | `brain.py:109`, `neurochemistry.py:108` |
| Química | 7 substâncias | meia-vida de 0,3 h (noradrenalina) a 4 h (serotonina) | `neurochemistry.py:37` |
| Emoção | 8 emoções, humor, energia | meia-vida de 5 min (surpresa) a 120 min (confiança) | `emotions.py:35` |
| Memória curta | até 7 lembranças | consolida acima de 0,45 de força | `memory.py:78-80` |
| Postura | a atitude da próxima fala | a cada experiência | `brain.py:487` |
| Vínculo | relação com quem conversa | meia-vida de 30 dias | `brain.py:193` |
| Memória longa | até 300 lembranças | meia-vida de 14 dias, freada por emoção e evocação | `memory.py:106` |
| Traços e caráter | OCEAN e os seis eixos morais | × plasticidade: `1/(1+n/40)`, piso 0,06 | `personality.py:219` |
| Valores | o que passou a importar | dezenas de experiências, com teto de soma 4,0 | `growth.py:151` |
| Estratégias | o que cada postura rendeu | média móvel, passo `max(0,3; 1/tentativas)` | `growth.py:207` |
| Propósito e princípios | o sentido da vida dele | revisto a cada 20 experiências ou quando o valor dominante muda | `brain.py:427` |

**A regra:** uma camada nunca pode mudar mais rápido que a camada abaixo dela. Se
uma mudança em `values` chegar a acontecer por causa de um único turno ruim, a
arquitetura quebrou, mesmo que os testes passem.

**O invariante importa mais que tudo:** `self_description` está em toda mensagem
(`identity_block`, `brain.py:525`) e nunca é reescrita. É a âncora que impede a
adaptação de dissolver o personagem. Nenhum módulo novo pode ter permissão de
escrever nela.

## Regras de acoplamento

O que mantém isto modular não é a divisão em arquivos — é quem tem caneta sobre o
quê.

1. **Dono único.** `Emotions` só é alterado por `emotions.py`; `Character` e
   `Traits` só por `personality.py`; e assim por diante. Os outros módulos passam
   *deltas* (`emotion_impact`, `character_impact`, `trait_deltas`), nunca atribuem
   valores.
2. **`Experience` é o contrato.** Toda comunicação entre "o que aconteceu" e "o que
   isso muda" passa por essa dataclass congelada (`experience.py:19`). Um módulo novo
   que precise de um canal próprio para falar com o `Brain` é sinal de que ele não é
   um módulo, é uma emenda.
3. **`brain.py` é o único que orquestra.** Módulo não chama módulo. `growth` não
   conhece `emotions`; quem cruza os dois é o `Brain`. Isso concentra a complexidade
   num lugar só — de propósito: é mais fácil defender um ponto do que treze.
4. **Escrita é sempre limitada.** Todo delta passa por `clamp` (`experience.py:13`) e
   é multiplicado por plasticidade. Nenhum caminho de escrita pode ser ilimitado.
5. **Aleatoriedade só pelo `Fate`.** Quem precisa de acaso pede a `self.fate.rng`.
   Nenhum módulo chama `random` global.

**Onde o código ainda não cumpre isto:** `Brain` tem cerca de trinta campos mutáveis
(`brain.py:71-105`) e vários deles — `volatility`, `resilience`, `luck` — são
escritos de dentro de `live()`, `_learn_outcome()` e `reflect()` sem dono claro
(`brain.py:256-257`, `:330`, `:395`). São exatamente os campos mais difíceis de
depurar. Se forem promovidos a um módulo próprio (um `Temperament` com dono e freio),
a regra 1 volta a valer inteira.

## Freios: por que o sistema não explode nem congela

Todo laço de realimentação aqui tem um contrapeso. Quem mexer em um lado precisa
mexer no outro.

| Laço | Sobe | Desce | Teto |
|---|---|---|---|
| Emoção | `apply` com ganho por traço e química | `decay` por meia-vida rumo ao basal | `clamp` 0..1 |
| Vínculo | valência do interlocutor × intensidade | meia-vida de 30 dias | `clamp` -1..1 |
| Volatilidade | adversidade (`:257`), resultado ruim (`:330`) | balanço positivo na reflexão (`:395`) | 0,05..0,95 |
| Caráter | deltas de experiência e de reflexão | plasticidade caindo com a idade | `clamp` -1..1 |
| Valores | `reinforce` por tags e por resultado | normalização quando a soma passa de 4,0 | 0..1 cada |
| Estratégias | recompensa observada | média móvel: a memória do passado dilui | -1..1 |
| Memória | força ao registrar, +0,1 por evocação | esquecimento com meia-vida de 14 dias | 300 itens |

E dois freios estruturais que valem para o sistema inteiro:

- **Plasticidade decrescente** (`personality.py:219`): a mesma experiência muda um
  recém-nascido dez vezes mais que um cérebro maduro. É o que faz o personagem
  *assentar* em vez de girar para sempre.
- **Exploração forçada** (`brain.py:514`): há uma chance pequena de tentar a postura
  menos usada. Sem isso, `StrategyMemory` trava na primeira postura que der certo e o
  personagem vira uma nota só — a "morte térmica" de qualquer sistema que só
  aproveita o que já conhece.

## O sinal de aprendizado (e o seu limite)

`_learn_outcome` (`brain.py:319`) é onde o cérebro decide que uma postura "funcionou":

```
recompensa = 0,60 × valência da resposta recebida
           + 0,25 × variação do vínculo
           + 0,15 × variação do humor
```

Isso alimenta `StrategyMemory` e, por tabela, reforça os valores que a postura
expressa (`growth.py:42`). É um sistema de aprendizado por reforço em miniatura, e é
o único lugar onde a palavra "adaptação" tem direção — em todo o resto, adaptar só
quer dizer mudar.

**O limite, dito às claras:** a recompensa é um proxy. Ela mede *o interlocutor
reagiu bem*, não *isto foi bom*. E `manipular` está entre as posturas
(`brain.py:44`), com valores próprios em `growth.py:42`. Um interlocutor que responde
bem à manipulação faz a recompensa subir, o que reforça os valores da manipulação, o
que puxa `moral_target` (`growth.py:169`) e, através dele, a moralidade do caráter
(`brain.py:459`). O caminho para o mal é **projetado** e faz parte da proposta do
pacote — mas ele é uma consequência do proxy, não uma escolha ética do sistema. Quem
mudar a fórmula da recompensa está mudando a moral do personagem, mesmo achando que
está mexendo em três coeficientes.

## Determinismo e reprodutibilidade

Um sistema adaptativo com acaso e estado persistido só é depurável se a
aleatoriedade for controlável. Situação atual:

**Determinístico (bom):**
- traços e caráter iniciais vêm de um hash da descrição (`personality.py:227`) — a
  mesma descrição sempre dá o mesmo ponto de partida;
- valores iniciais e genética derivam do mesmo `seed` (`growth.py:140`,
  `neurochemistry.py:108`);
- o ruído de `decide_stance` usa `random.Random(seed + experience_count)`
  (`brain.py:517`) — reprodutível por construção;
- os testes injetam `Fate(random.Random(n))` (`tests/test_cerebro.py:38`), que é a
  forma correta e já suportada de fixar o acaso.

**Não determinístico (a dívida):**
- `Fate()` sem argumento usa entropia do sistema (`fate.py:107`) — correto em
  produção, mas quer dizer que nenhum bug de deriva reproduz sem antes ser isolado;
- **o estado do gerador não é salvo**: `to_dict` guarda só `fate_rate` e `whim_rate`
  (`brain.py:707-708`). Depois de um `save`/`load`, o fluxo de sorteios recomeça.
  Uma sessão longa não é reprodutível ponta a ponta nem com semente fixa;
- `decide_stance` mistura duas fontes de acaso, a semeada e a do `Fate`
  (`brain.py:511-518`), então nem esse trecho é reprodutível sozinho.

**Regra para quem mexer:** nenhum caminho novo pode chamar `random` diretamente. Se
o acaso precisar sobreviver a um `save`, o estado do gerador (`rng.getstate()`) tem
de entrar no dicionário serializado.

## Estado persistido e versão

`to_dict` (`brain.py:683`) grava `"version": 1`. **`from_dict` (`brain.py:725`) nunca
lê esse campo.** Compatibilidade hoje é feita inteiramente de `data.get(chave,
padrão)` — funciona para acrescentar campo, e falha em silêncio para qualquer coisa
além disso: um campo cujo significado muda faz cérebros antigos recarregarem como
outra pessoa, sem erro nenhum.

Como o estado é adaptativo, isso é mais grave do que numa configuração comum: o
arquivo salvo **é** o personagem. Perder a fidelidade do carregamento é perder a
história vivida.

**Regra para quem mexer:**

- campo novo com padrão neutro → mantém `version: 1`, use `.get`;
- significado alterado, campo removido, escala mudada → **suba a versão** e escreva a
  migração em `from_dict`, antes da construção;
- carregar uma versão maior que a conhecida deve falhar com mensagem clara, nunca
  seguir com defaults.

## Como testar um sistema que muda sozinho

Teste unitário não alcança comportamento emergente. Os três níveis que funcionam
aqui:

1. **Unitário, com o acaso desligado.** `Fate(rate=0.0, whim_rate=0.0)` mais um
   relógio injetado (`Session.clock`, `session.py:125`) tornam um turno inteiro
   determinístico. É assim que `tests/test_cerebro.py` verifica efeito de uma
   experiência isolada.
2. **De invariante.** Rode centenas de experiências e verifique **propriedades**, não
   valores: todo eixo dentro do intervalo, memória longa dentro da capacidade, soma
   dos valores sob o teto, plasticidade monotonicamente decrescente, `self_description`
   intacta. Invariante que se mantém sob ruído é a única prova de que os freios
   funcionam.
3. **De trajetória.** Um roteiro fixo de experiências com semente fixa deve produzir
   sempre o mesmo caráter final. É o teste que pega regressão de ordem — aquele em
   que alguém trocou dois passos de `live()` e nada mais acusou.

O nível 3 depende de resolver a dívida de reprodutibilidade acima; hoje ele só vale
dentro de um processo, sem passar por `save`/`load`.

## Riscos conhecidos

Em ordem de custo para consertar depois:

1. **Estado de `Fate` não persistido** — quebra reprodutibilidade em toda sessão
   salva. (`brain.py:707`)
2. **`version` gravada mas não lida** — nenhuma rede de proteção para migração.
   (`brain.py:725`)
3. **Campos de temperamento sem dono** — `volatility`, `resilience` e `luck` são
   escritos em quatro lugares diferentes com constantes mágicas. (`brain.py:256`,
   `:330`, `:395`)
4. **Ordem de `live()` implícita** — o comportamento depende dela e nada no código
   avisa. Este documento é a mitigação atual; um teste de trajetória seria melhor.
5. **Recompensa por proxy** — mede reação, não valor, e por isso pode premiar
   manipulação. (`brain.py:319`)
6. **Constantes espalhadas** — os `0.05`/`0.03`/`0.02` de `live()` são as taxas de
   adaptação do sistema e deveriam estar declaradas junto, com nome, não embutidas no
   fluxo.
7. **`Brain` grande demais** — 783 linhas e ~30 campos. Ainda gerenciável, mas é a
   fronteira onde "modular" começa a ser só uma descrição das pastas.

## Checklist para acrescentar um módulo

Antes de escrever a primeira linha de um módulo novo, responda por escrito:

- [ ] **Que pedaço do estado ele possui, e ninguém mais escreve?**
- [ ] **Em que velocidade ele muda?** Encaixe-o na tabela de camadas. Se ele muda
      mais rápido que a camada que influencia, repense.
- [ ] **Qual é o freio?** Todo acumulador precisa de teto e de caminho de volta.
- [ ] **Onde ele entra em `live()` e por quê nessa posição?** Atualize o diagrama
      deste documento na mesma alteração.
- [ ] **Ele usa acaso?** Então pede ao `Fate`, nunca ao `random` global.
- [ ] **Ele entra no estado salvo?** Então tem `to_dict`/`from_dict` próprios, com
      padrão neutro para cérebros que nasceram antes dele.
- [ ] **Ele aparece no implante?** Só se muda a fala. Estado que o modelo nunca vê é
      peso morto no prompt.
- [ ] **Que invariante ele não pode violar?** No mínimo: `self_description`,
      `seed`, `born_at`.

Um módulo que não passa por essa lista não é um módulo — é mais um campo no
`Brain`, e o custo dele aparece daqui a duzentas experiências, longe de onde foi
escrito.
