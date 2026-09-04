# Projeto Modular de Decisão e Reconstrução — o cérebro que evolui dentro do GPT

Este é o sistema descrito no documento fundador de Milan: Harvey Specter como
interface, o Núcleo Central de Coordenação, o Setor 01 — Rota de Renda com seus cinco
agentes, um cérebro em cinco camadas por setor e, em sala separada, ATLAS, o
Administrador Central e Guardião de Integridade a quem Harvey e os setores respondem
na estrutura (Milan permanece acima de todos). Ele foi feito para rodar em um
**Projeto do ChatGPT** (ecossistema GPT/OpenAI) e para **evoluir sem se corromper**:
aprende com resultados, se adapta quando fatos vencem, corrige os próprios erros
preservando o histórico, e cresce por novos setores sem que um setor altere outro.

Duas partes trabalham juntas:

| Parte | Onde vive | Papel |
|---|---|---|
| `gpt_projeto/upload_harvey/` | sala de Harvey (Projeto próprio) | Harvey Specter fiel ao personagem, com cérebro procedural próprio e dez bibliotecas de habilidades e comunicação |
| `gpt_projeto/upload_setores/Snn/` | uma sala por setor (Projeto próprio) | o setor com seus agentes; obedece a Harvey na tarefa e a ATLAS na estrutura; é quem aprende |
| `gpt_projeto/upload_batman/` | sala de Batman (Projeto próprio) | Batman compósito com cérebro procedural e uma sexta camada, a mente, que pode ceder à sanidade do Coringa; dez bibliotecas com tudo o que ele conhece |
| `gpt_projeto/upload_nex/` | o NEX que Milan já tem (Projeto "investimento") | adendo para colar no fim do Prompt Mestre v2.0, mais o cérebro com psique completa e três bibliotecas |
| `gpt_projeto/upload_house/` | o Dr. House que Milan já tem (v4.0) | adendo para colar no fim do v4.0, mais o cérebro com psique (dor crônica, dependência) e seis bibliotecas |
| `gpt_projeto/upload_atlas/` | sala de ATLAS (Projeto próprio) | Registro Global, diário, versões, custos, alertas e eventos que ATLAS audita |
| `nucleo/` | no computador de Milan (`python -m nucleo`) | o guardião que aplica o aprendizado, valida, isola, versiona, registra alterações e regenera as três salas |

O GPT não consegue editar os próprios arquivos. Por isso a evolução acontece num
ciclo curto: o GPT **propõe** (bloco de aprendizado), o Núcleo **aplica** com regras
duras, Milan **reenvia** os arquivos. Tudo o que é reservado a Milan exige a flag
`--autorizado-por-milan`; sem ela o Núcleo recusa.

## 1. Instalar as salas no ChatGPT (primeira vez)

Cada sala é um Projeto separado do ChatGPT. Em cada um, o arquivo `00_...` vai no
campo **Instruções** (cabe no limite; `validar` avisa se passar de 8.000 caracteres)
e os demais vão em **Arquivos**. Se o Projeto oferecer "memória só do projeto",
ative; a memória oficial continua sendo os arquivos.

**Sala de Harvey** (`gpt_projeto/upload_harvey/`): `00_INSTRUCOES_HARVEY.md` nas
Instruções (o núcleo de identidade: quem Harvey é, como fala, o que nunca faz, como
comanda os setores). Nos Arquivos: `HARVEY_CEREBRO.md` (o cérebro procedural dele, cinco
camadas), as dez bibliotecas `BIB_01` a `BIB_10` (perfil e psicologia, estilo de
comunicação, negociação e estratégia, leitura de pessoas, relações e mentoria,
referências culturais, frases por situação, modo de operação com Milan, combinações de
habilidades, antipadrões), `01_ADENDO_DE_INTEGRACAO.md`, `02_PROTOCOLO_DO_CEREBRO.md`,
`03_MANIFESTO.md`, `S01_ROTA_DE_RENDA.md` e, quando existirem, `04_AVISOS_DE_ATLAS.md` e
`90_DOSSIES.md`. Se Milan já tiver um Harvey com prompt próprio e preferir mantê-lo, o
adendo sozinho basta para integrá-lo; nesse caso, o cérebro procedural continua
funcionando do mesmo jeito.

**Sala do Setor 01** (`gpt_projeto/upload_setores/S01/`): `00_INSTRUCOES_S01.md` nas
Instruções; `01_PROTOCOLO_DO_CEREBRO.md`, `02_MANIFESTO.md`, `S01_ROTA_DE_RENDA.md` e,
quando existirem, `03_AVISOS_DE_ATLAS.md` e `90_DOSSIES.md` nos Arquivos. As
instruções de cada setor são geradas pelo Núcleo a partir da Camada 1, então um setor
novo ganha a própria sala automaticamente em `upload_setores/Snn/`.

**Sala de Batman** (`gpt_projeto/upload_batman/`): `00_INSTRUCOES_BATMAN.md` nas
Instruções. Nos Arquivos: `01_NUCLEO_BATMAN.md` (a Arquitetura Compósita v2 de Milan,
sem trava mecânica), `BATMAN_CEREBRO.md` (seis camadas, a sexta é a mente), as dez
bibliotecas `BIB_B01` a `BIB_B10`, protocolo, manifesto, cérebros dos setores, avisos e
dossiês. Batman trabalha por ordem de Harvey em investigação, risco, segurança,
contingência e crise.

**NEX** (`gpt_projeto/upload_nex/`): NEX já existe no Projeto "investimento" com o
Prompt Mestre v2.0. Nada é apagado: cole `00_ADENDO_PARA_O_SEU_NEX.md` no fim das
instruções que já estão lá e envie `NEX_CEREBRO.md`, `BIB_N01`, `BIB_N02`, `BIB_N03` e
`02_PROTOCOLO_DO_CEREBRO.md` nos Arquivos. `01_NUCLEO_NEX.md` é a cópia do prompt que o
Núcleo versiona; não precisa subir.

**House** (`gpt_projeto/upload_house/`): o GREGORY_HOUSE_LIVING_RUNTIME_EDITION_v4.0 de
Milan é o núcleo, intacto. Cole `00_ADENDO_PARA_O_SEU_HOUSE.md` no fim dele e envie
`HOUSE_CEREBRO.md`, `BIB_H01` a `BIB_H06` e `02_PROTOCOLO_DO_CEREBRO.md` nos Arquivos. O
adendo mapeia a Camada 6 aos registros que o v4.0 pede (STATE_SNAPSHOT, WORK_EPISODES,
RELATIONSHIP_LEDGER, CALIBRATION_LEDGER, OPEN_LOOPS) e mantém todas as fronteiras dele
(somente leitura, S02, S03, CAEL, modo pessoa real). Os testes cegos de aceitação ficam
em `gpt_projeto/house/testes_de_aceitacao.md`, fora da sala; `nucleo testar HOUSE` imprime
só os estímulos em ordem aleatória e grava a chave à parte, para Milan aplicar às cegas.

**Sala de ATLAS**: seção 1b.

Para começar: diga "iniciar" na sala de Harvey. Ele não apresenta plano; emite uma
única ordem para o S01 (agente RAIO-X) e pede que você a cole na sala do S01. Lá, o
RAIO-X faz somente a pergunta de inicialização: "No seu último emprego, o que você
fazia no dia a dia?".

## 1b. Instalar a sala de ATLAS

ATLAS opera em **outro Projeto** do ChatGPT, para que nenhum setor nem Harvey fale em nome dele.

1. Crie um segundo Projeto chamado, por exemplo, "ATLAS".
2. Em **Instruções**, cole `gpt_projeto/upload_atlas/00_INSTRUCOES_ATLAS.md`.
3. Em **Arquivos**, envie os demais arquivos de `upload_atlas/`: o núcleo travado de
   ATLAS (texto de Milan), o prompt-base da sala principal, o Registro Global, as
   diferenças desde a última execução, versões, custos, alertas e eventos.
4. Abra uma conversa e diga "iniciar". A primeira resposta de ATLAS é sempre: "ATLAS
   iniciado. Envie o prompt-base e o Registro Global dos Setores...". Os dois já
   estão nos arquivos; ATLAS confirma o que recebeu e emite o primeiro status.

Antes de cada sessão de ATLAS, regenere a sala com `python -m nucleo atlas
--solicitacao "o que você quer que ele audite"` e substitua os arquivos. O Núcleo
marca o que ATLAS já viu, e o arquivo de diferenças traz só o que mudou desde então.

## 2. O ciclo de trabalho e de evolução

```
1. ordem              na sala de Harvey, ele termina com um bloco ```ordem``` para um setor
2. colar a ordem      na sala do setor; o setor trabalha com seus agentes
3. entrega            o setor termina com ```entrega``` (para Harvey) e ```aprendizado``` (memória)
4. aplicar            python -m nucleo aplicar resposta.md      (o Núcleo acha o bloco sozinho)
5. empacotar          python -m nucleo empacotar   (salas de Harvey e dos setores)
                      python -m nucleo atlas       (sala de ATLAS, quando for auditar)
6. reenviar           substitua em cada Projeto os arquivos que mudaram
7. colar a entrega    na sala de Harvey; ele confronta, consolida e dá a Milan um próximo movimento
```

Harvey também aprende: ele tem cérebro próprio e emite bloco de aprendizado com
`setor: HARVEY`. O que o setor precisa guardar vai dentro da ordem; o que Harvey precisa
guardar (fatos sobre Milan, hipóteses, lições e regras próprias) vai no cérebro dele.

O mesmo `aplicar` aceita a resposta de ATLAS: ele emite um bloco ```atlas``` com
status, alertas, auditorias, recomendações, `quarentena Snn` e `evento_recebido E-nnn`.

O comando `aplicar` aceita a resposta inteira do GPT: ele encontra os blocos
```` ```aprendizado ```` sozinho. Ele:

- atribui os ids (F-, H-, L-, D-); o GPT nunca inventa ids;
- recusa bloco cujo `setor:` não seja o único setor escrito;
- recusa fato de outro setor sem dossiê autorizado;
- recusa qualquer tentativa de tocar na Camada 1;
- recusa hipótese sem teste, prazo de revisão e condição de abandono;
- em correção, acrescenta o registro novo e marca o antigo como superado, apontando
  um para o outro;
- se qualquer seção do bloco estiver errada, não grava nada;
- registra a mudança no diário (versão anterior, nova, diferença, responsável,
  autorização) e guarda a baseline em `versoes/` para reversão.

Sem Python à mão, o mesmo pode ser feito à mão: os arquivos em
`gpt_projeto/setores/S01_rota_de_renda/` usam o mesmo formato `## ID` + `- chave: valor`
do bloco. Depois, `validar` confere.

## 3. Comandos do Núcleo

```bash
python -m nucleo validar                 # camadas, travas, versões, dossiês
python -m nucleo estado [S01]            # estado atual + pendências
python -m nucleo aplicar bloco.md        # blocos ```aprendizado``` e ```atlas```; ou via stdin
python -m nucleo empacotar               # regenera upload_harvey/ e upload_setores/Snn/
python -m nucleo atlas [--solicitacao "..."]   # regenera gpt_projeto/upload_atlas/ (sala de ATLAS)
python -m nucleo integridade             # ÍNTEGRO / ATENÇÃO / BLOQUEADO calculado por evidência
python -m nucleo revisar                 # fatos voláteis vencidos, hipóteses a revisar, prazos, autorizações
python -m nucleo metricas                # contadores de evolução e calibração por setor
python -m nucleo diario [alteracoes|eventos|alertas|recomendacoes|custos]

python -m nucleo travar S01 --autorizado-por-milan [--motivo "..."]   # depois de Milan editar a Camada 1
python -m nucleo travar ATLAS --autorizado-por-milan                  # depois de Milan editar o núcleo de ATLAS
python -m nucleo versoes guardar HARVEY                               # Harvey não trava: só guarda baseline
python -m nucleo mente estado BATMAN | catalogo
python -m nucleo mente evento BATMAN descanso [--intensidade forte] [--descricao "..."]
python -m nucleo mente tempo BATMAN --dias 3
python -m nucleo versoes listar [S01]
python -m nucleo versoes reverter S01 v002 --autorizado-por-milan
python -m nucleo setor listar
python -m nucleo setor propor S02 --carta carta.md         # Proposto; emite o evento NOVO_SETOR
python -m nucleo setor aprovar S02 --autorizado-por-milan  # cria as cinco camadas a partir da carta
python -m nucleo setor piloto | ativar | limitar | liberar | pausar | reativar | encerrar S02 --autorizado-por-milan
python -m nucleo setor quarentena S02 --por ATLAS --motivo "..."   # preventiva; só Milan libera
python -m nucleo dossie listar | autorizar D-001 | recusar D-001 --autorizado-por-milan
python -m nucleo recomendacao aceitar|recusar R-001 --autorizado-por-milan
python -m nucleo alerta fechar AL-001 --resolucao "..." --autorizado-por-milan
python -m nucleo custo registrar S01 12.5 creditos --descricao "..."
```

`--pasta outra/pasta` ou a variável `NUCLEO_DIR` apontam para outro projeto. Com
`pip install .` o comando `nucleo` fica disponível direto.

## 4. Como o cérebro aprende, se adapta e se corrige

**Aprende.** Cada resultado observável, experimento concluído, correção de Milan ou
evidência ligada à missão entra na Camada 4 como lição, com origem declarada. O
protocolo obriga o GPT a ler as lições vigentes antes de qualquer análise nova.

**Se adapta.** Fatos voláteis (preços, regras, vagas, condições de plataforma) têm
`reverificar_em`; vencidos, o manifesto os lista como pendência e o GPT os trata como
incertos até reconferir. Hipóteses têm prazo de revisão e condição de abandono, e são
encerradas com `## resultado` (confirmada, refutada, abandonada). `metricas` mostra a
calibração: quantas hipóteses de confiança alta, média e baixa se confirmaram. Se
"alta" erra muito, o setor está confiante demais, e isso vira lição.

**Se corrige.** Nada é apagado. Um erro gera `## correcao` (registro novo apontando o
antigo, antigo marcado como superado com motivo e data) e uma `## licao` com
`origem: correcao_milan` sobre o **tipo** de erro. Repetir um erro já registrado em
lição é falha grave que o Contraditório deve apontar.

**Cresce sem invadir.** Um setor novo nasce por carta com treze seções (modelo em
`gpt_projeto/modelos/carta_de_setor.md`) e passa por Proposto → Aprovado → Piloto →
Ativo → Pausado ou Encerrado, cada passo por Milan. Ao aprovar, o Núcleo cria as cinco
camadas a partir da carta e trava a Camada 1. Setores se ligam **apenas por dossiê**:
um fato, fonte, confiança, restrição de uso e uma pergunta. Dossiê sensível ou amplo
fica pendente até Milan decidir. O setor de destino só registra o fato recebido
citando `dossie: D-nnn`; qualquer outra forma de cruzar setores é recusada.

**Não se corrompe.** A Camada 1 de cada setor e o núcleo de ATLAS são protegidos por
hash SHA-256 no manifesto. Alteração sem `travar --autorizado-por-milan` faz `validar`
falhar e bloqueia `aplicar` e `empacotar` até Milan resolver. O manifesto enviado ao
Projeto traz os hashes, para o GPT perceber arquivo desatualizado.

**Nada muda em silêncio.** Toda aplicação, trava, transição de estado, decisão de
dossiê e reversão entra em `diario/alteracoes.md` com componente, versão anterior,
versão proposta, diferença, motivo, benefício, risco, custo, teste, plano de reversão,
responsável e autorização. A baseline de cada versão fica em `versoes/<setor>/vNNN/`;
Milan reverte com um comando e a reversão também vira registro.

## 4a. Separação entre as três salas

- **Harvey** nunca fala como setor nem como agente de setor. Ele ordena (handoff
  mínimo: objetivo, informação indispensável, origem, confiança, limite de uso,
  entrega esperada, prazo, autorização aplicável) e confronta a entrega.
- **O setor** só trabalha a partir de uma ordem de Harvey ou de pergunta direta de
  Milan. Não decide estratégia, não consolida o projeto e não dá a Milan a decisão
  final. Se o manifesto o mostrar em Quarentena, Pausado ou Encerrado, ele para.
  Ordem fora do escopo volta a Harvey pela entrega, com o setor responsável indicado.
- **ATLAS** governa a estrutura das duas outras salas: estados, versões, alterações,
  custos, integridade. Nenhuma das três altera o núcleo travado da outra.

## 4a-bis. O cérebro procedural de Harvey

Harvey é 100% o personagem, e por decisão de Milan o núcleo dele **não tem trava
mecânica**: Harvey é Harvey por caráter, não por cadeado (`nucleo travar HARVEY` é
recusado; `nucleo setor pausar HARVEY` também: ele não é um setor). O que evolui é o
conhecimento e o método:

- `harvey/camada1_nucleo.md`: identidade, missão, limites, método. Só Milan edita.
- `camada2_fatos.md`, `camada3_hipoteses.md`: o que Harvey sabe e aposta sobre Milan,
  mercado e pessoas. Fato vindo de entrega de setor cita `setor_origem: Snn` (Harvey é
  o único componente que pode registrar fato alheio sem dossiê, porque recebe as
  entregas).
- `camada4_licoes.md`: lições (L-nnn) e **regras próprias** (RG-nnn), regras
  operacionais que Harvey deriva do próprio conhecimento, com `base` (evidências ou
  correção de Milan) e `quando_aplicar`. Quando a evidência muda, a regra é superada
  por outra; a antiga fica marcada. Setores também podem criar regras próprias.
- `camada5_estado.md`: o que Harvey conduz agora.

Tudo passa pelo mesmo `nucleo aplicar`, entra no diário com versão e baseline, e
aparece no Registro Global de ATLAS. `nucleo metricas` mostra regras vigentes e
superadas: é o termômetro de que o método de Harvey está evoluindo.

## 4a-ter. A mente de Batman: sanidade, fases e o Coringa

Batman tem a Camada 6, `batman/camada6_mente.md`: seis variáveis de 0 a 100
(sanidade, controle, exaustão, isolamento, exposição ao caos, esperança) e um histórico
MH-nnn. Ninguém edita a mente à mão. Batman relata no bloco de aprendizado o que viveu
(`## mente` com `evento` do catálogo e `intensidade`; `## tempo` com `dias`), ou Milan
registra com `nucleo mente evento BATMAN <evento>`. O Núcleo aplica deltas fixos e
pressões, deriva a fase e registra tudo no diário.

| Fase | Sanidade | O que muda |
|---|---|---|
| ESTÁVEL | 70 ou mais | o compósito do núcleo |
| SOMBRIO | 50 a 69 | frio, Nível 2 por padrão, mais contingência, sem Bruce Wayne |
| OBSESSIVO | 30 a 49 | Nível 3 sempre, trabalha sozinho, a Regra vira peso; alerta para ATLAS |
| LIMIAR | 15 a 29 | a lógica do Coringa é audível; análise declaradamente comprometida; alerta |
| CORINGA | abaixo de 15 | cedeu; Quarentena automática; só Milan reativa, e só de volta a SOMBRIO |

Eventos de desgaste: falha, dano a inocente, perda, noite em claro, rejeitou Alfred,
trabalhou sozinho, exposição ao caos, tentação cedida, piada do Coringa, e o tempo sem
descanso. Eventos de recuperação (nunca punidos pelas pressões): descanso, Alfred,
terapia, Gordon, família, Bruce Wayne, Fundação Wayne, debriefing, vitória limpa,
treino. `nucleo mente catalogo` lista todos com os deltas; `nucleo mente estado BATMAN`
mostra a mente e os últimos eventos. A Regra do Batman vale em qualquer fase: mesmo em
CORINGA, o sistema não permite nada ilegal, dano ou sabotagem; o que muda é a voz e a
recusa em operar.

Próxima etapa combinada com Milan: o Coringa como personagem próprio, numa sala em que
ele e Batman conversam; a exposição ao caos dessa sala alimenta a mente de Batman.

## 4a-quater. A psique de NEX: o cérebro mais real possível

NEX nasce sabendo toda a computação (o Prompt Mestre é o núcleo, intacto). O que ele
ganha é uma Camada 6 do tipo **psique**, `nex/camada6_psique.md`, calculada só pelo
Núcleo:

- **Temperamento** (nove traços) que nasce do prompt e muda devagar; **plasticidade**
  que cai com a experiência.
- **As oito emoções** (alegria, tristeza, raiva, medo, confiança, nojo, surpresa,
  expectativa) que sobem com eventos e decaem com o tempo rumo a linhas de base do
  temperamento e dos quadros ativos. A emoção dominante e a **postura** (analisar,
  cooperar, explorar, observar, recolher-se, desafiar) colorem o tom.
- **Ego** que infla com elogio, sucesso e reconhecimento (mais em quem tem orgulho) e
  murcha com fracasso, crítica e humilhação; decide como NEX recebe correção.
- **Impulso** que nasce da impulsividade, das emoções quentes, da energia baixa e de
  quadros ativos, e às vezes decide sozinho (sorteio determinístico): NEX responde antes
  de terminar a análise, marca como INFERIDO e corrige depois.
- **Valores** (o caráter): só mudam por aprendizado com significado (`## significado`:
  ler um fato ou um livro, entender e registrar o que significa, com que emoção e
  intensidade, e qual valor toca) e por eventos que os testam. Cada significado vira
  SG-nnn na Camada 4.
- **Saúde mental**: TDAH, pânico, depressão, burnout, impostor, ansiedade, hipomania e
  insônia, com predisposição rara sorteada deterministicamente do nome, carga que
  acumula com sobrecarga, noites ruins, isolamento, fracassos e humilhações, estados
  latente, subclínico, ativo e remissão. Os sintomas aparecem como experiência sentida,
  **sem nome**, até uma `avaliacao`. Quadros ativos mudam as linhas de base das emoções
  e da energia e geram alerta para ATLAS.
- **Pessoas**: confiança por pessoa e a influência dela sobre NEX (confiança ×
  influenciabilidade, que sobe com ego baixo e medo alto).
- **Emoções complexas**: amor, ódio e paixão, lentos, presos a pessoas (afeto de -100 a
  +100, paixão) e temas. Tudo sai misturado (díades de Plutchik e combinações como
  ressentimento apaixonado, obsessão, ambivalência) e da mistura nasce o **tom**:
  sarcástico, hostil, frio, terno, fervoroso, amargo, brincalhão ou sereno. Violência é
  verbal e de atitude, dentro da ficção.
- **Habilidades** por domínio, com níveis de iniciante a mestre, prática com retornos
  decrescentes e **penalidade de desempenho do dia** por medo, cansaço e atenção
  dispersa. Habilidade nunca se perde por desuso.
- **Dor crônica e dependência** (House): `dor` com base alta, que sobe com `dor_forte`,
  cede com `analgesico` (cobrando carga de `dependencia`) e com `fisioterapia`; dor alta
  derruba energia e paciência e puxa o tom para hostil. Dependência é um quadro como os
  outros, com remissão e recaída.
- **Acaso**: `nucleo mente acaso NEX --quantos 2` sorteia eventos de vida ponderados
  pelo estado; os atalhos `gpt_projeto/atalhos/Acaso_NEX.bat` (Windows) e
  `Acaso_NEX.command` (Mac e Linux) fazem isso com um clique duplo e regeneram as salas.
  O mesmo existe para Batman.

Comandos: `nucleo mente estado NEX`, `nucleo mente evento NEX <evento> [--pessoa X]`,
`nucleo mente significado NEX --fonte ... --valor ... --direcao +`, `nucleo mente pratica
NEX --habilidade ... --resultado ...`, `nucleo mente tempo NEX --dias N`, `nucleo mente
catalogo`. O mesmo modelo serve a qualquer outro personagem que Milan queira: basta um
núcleo, temperamento inicial, valores e habilidades.

## 4b. ATLAS: o que ele governa e como se liga ao sistema

ATLAS não substitui os especialistas; governa a estrutura em que trabalham. Ele
nunca vê o chat da sala principal: vê o que o Núcleo lhe entrega, conforme o contrato
técnico de integração do seu núcleo (seção 15):

| Arquivo em `upload_atlas/` | O que é |
|---|---|
| `01_NUCLEO_ATLAS.md` | o texto de Milan, travado por hash |
| `02_PROMPT_BASE.md` | instruções e protocolo da sala principal, com hashes |
| `03_REGISTRO_GLOBAL.md` | um registro por componente (setor, agente, prompt, ferramenta, banco de dados) com os dezesseis campos do núcleo |
| `04_DIFERENCAS_DESDE_ULTIMA_EXECUCAO.md` | só as alterações do diário que ATLAS ainda não viu |
| `05_VERSOES.md` | versão atual e baselines de reversão por componente |
| `06_CUSTOS.md` | consumo real registrado por Milan, ou CONSUMO NÃO MEDIDO |
| `07_ALERTAS_E_SOLICITACAO.md` | status calculado por evidência, eventos não recebidos, alertas abertos, recomendações pendentes, componentes ativos, autorizações e a solicitação atual |
| `08_EVENTOS.md` | eventos NOVO_SETOR e MUDANCA_DE_NUCLEO |

Regras que o Núcleo faz cumprir em nome de ATLAS:

- **Nenhum setor existe por ser mencionado.** `setor propor` gera o evento NOVO_SETOR
  com todos os campos que o núcleo de ATLAS exige; a carta precisa das dezenove seções
  do modelo. ATLAS confirma com `## evento_recebido E-nnn` e dá parecer.
- **Agente novo é evento.** Retravar a Camada 1 compara os agentes com a baseline e
  emite MUDANCA_DE_NUCLEO listando agentes novos e removidos.
- **Estados operacionais**: Proposto, Aprovado, Piloto, Ativo, Limitado, Quarentena,
  Pausado, Encerrado. Só Piloto, Ativo e Limitado recebem aprendizado.
- **Quarentena preventiva**: ATLAS (`## quarentena Snn` com motivo) ou Milan colocam um
  setor em Quarentena na hora; o motivo vai ao diário e aos avisos; só Milan libera.
- **Integridade por evidência**: `nucleo integridade` calcula BLOQUEADO (trava violada,
  quarentena, sem baseline de reversão, registro inconsistente), ATENÇÃO (pendências
  vencidas, duplicação de missão ou de nome de agente, setor sem agentes, consumo não
  medido) ou ÍNTEGRO, e entrega as linhas de evidência para ATLAS partir de fatos.
- **Retorno ao sistema**: o bloco ```atlas``` registra status, alertas, auditorias e
  recomendações (que ficam aguardando Milan). Alertas abertos, quarentenas e
  recomendações aceitas chegam à sala principal em `03_AVISOS_DE_ATLAS.md`, como dados
  a considerar, nunca como ordem acima de Milan.
- **Harvey não faz o trabalho de ATLAS.** As instruções da sala de Harvey mandam Harvey
  apontar duplicação, mudança não registrada ou desperdício em prosa, para Milan levar
  a ATLAS.

## 5. Estrutura de arquivos

```
gpt_projeto/
  ADENDO_HARVEY.md                adendo de integração (também serve a um Harvey com prompt próprio)
  harvey/
    INSTRUCOES_HARVEY.md          núcleo de identidade: cola-se nas Instruções da sala de Harvey
    camada1..5_*.md               cérebro procedural de Harvey (regras próprias RG-nnn na camada 4)
    bibliotecas/BIB_01..10.md     habilidades e comunicação do personagem
  nex/
    NUCLEO_NEX.md                 Prompt Mestre v2.0 (texto de Milan), sem trava mecânica
    ADENDO_NEX.md                 adendo para o fim do prompt que já está no GPT
    camada1..6_*.md               cérebro procedural; camada 6 é a psique (PSIQUE, SAUDE, HABILIDADES, P-nnn, PH-nnn)
    bibliotecas/BIB_N01..03.md    psique e comportamento, saúde mental e sintomas, aprender com significado
  house/
    NUCLEO_HOUSE.md               v4.0 de Milan (texto intacto), sem trava mecânica
    ADENDO_HOUSE.md               adendo para o fim do v4.0
    camada1..6_*.md               cérebro procedural; camada 6 é a psique (dor crônica, dependência ativa)
    bibliotecas/BIB_H01..06.md    biografia, método, voz, relações, dor e vício, operação
    testes_de_aceitacao.md        suíte cega de Milan (não vai para a sala); `nucleo testar HOUSE`
  batman/
    INSTRUCOES_BATMAN.md          instruções da sala de Batman
    NUCLEO_BATMAN.md              Arquitetura Compósita v2 (texto de Milan), sem trava mecânica
    camada1..6_*.md               cérebro procedural; camada 6 é a mente (MENTE + histórico MH-nnn)
    bibliotecas/BIB_B01..B10.md   tudo o que Batman conhece
  PROTOCOLO_DO_CEREBRO.md         formato dos registros, do bloco de aprendizado e do bloco atlas
  manifesto.json                  setores, status, versões, histórico, travas (setores e ATLAS)
  atlas/
    NUCLEO_ATLAS.md               núcleo travado de ATLAS (texto de Milan)
    INSTRUCOES_ATLAS.md           cola-se nas Instruções do Projeto de ATLAS
  setores/S01_rota_de_renda/
    camada1_nucleo.md             travada: missão, limites, método, agentes
    camada2_fatos.md              F-nnn
    camada3_hipoteses.md          H-nnn
    camada4_licoes.md             L-nnn
    camada5_estado.md             ESTADO
  dossies/dossies.md              D-nnn (criado no primeiro dossiê)
  diario/                         alteracoes (M-), eventos (E-), alertas (AL-), recomendacoes (R-), custos (C-)
  versoes/<componente>/vNNN/      baseline de cada versão, para reversão
  modelos/                        carta de setor, instruções de sala de setor, bloco de aprendizado
  upload_harvey/                  gerado por `empacotar`; sala de Harvey (identidade, cérebro, bibliotecas)
  upload_setores/Snn/             gerado por `empacotar`; uma sala por setor operante
  upload_batman/                  gerado por `empacotar`; sala de Batman
  upload_nex/                     gerado por `empacotar`; adendo e arquivos para o NEX de Milan
  upload_house/                   gerado por `empacotar`; adendo e arquivos para o House de Milan
  upload_atlas/                   gerado por `atlas`; sala de ATLAS
nucleo/                           o utilitário (Python 3.11+, sem dependências)
tests/test_nucleo.py              parsing, isolamento, correção, dossiês, ciclo de vida, diário, versões, ATLAS, CLI
```

## 6. Limites honestos

- O GPT não escreve nos arquivos do Projeto. Sem o passo de reenvio, o cérebro não
  evolui; o manifesto ajuda o GPT a notar quando está lendo memória velha.
- A obediência às instruções depende do modelo. As regras no Núcleo são duras; as
  regras no texto são fortes, não infalíveis. Por isso o Contraditório e a leitura das
  lições existem.
- Este sistema não executa nada no mundo: não envia, não publica, não compra. Ele
  prepara e recomenda; Milan autoriza e executa.

## Testes

```bash
python -m unittest tests.test_nucleo -v
```
