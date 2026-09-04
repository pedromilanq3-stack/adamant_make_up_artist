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
| `gpt_projeto/upload_harvey/` | o Harvey que Milan já tem | adendo curto de integração para colar nas instruções dele, mais os arquivos que ele lê |
| `gpt_projeto/upload_setores/Snn/` | uma sala por setor (Projeto próprio) | o setor com seus agentes; obedece a Harvey na tarefa e a ATLAS na estrutura; é quem aprende |
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

**O seu Harvey** (`gpt_projeto/upload_harvey/`): Milan já tem um Harvey com prompt
próprio. Não o substitua. Cole `00_ADENDO_PARA_O_SEU_HARVEY.md` no fim das instruções
que ele já tem (o adendo é curto e não redefine identidade; só ensina as salas, os
arquivos, a ordem e a entrega). Envie `01_PROTOCOLO_DO_CEREBRO.md`, `02_MANIFESTO.md`,
`S01_ROTA_DE_RENDA.md` e, quando existirem, `03_AVISOS_DE_ATLAS.md` e `90_DOSSIES.md`
nos Arquivos do Projeto dele.

**Sala do Setor 01** (`gpt_projeto/upload_setores/S01/`): `00_INSTRUCOES_S01.md` nas
Instruções; `01_PROTOCOLO_DO_CEREBRO.md`, `02_MANIFESTO.md`, `S01_ROTA_DE_RENDA.md` e,
quando existirem, `03_AVISOS_DE_ATLAS.md` e `90_DOSSIES.md` nos Arquivos. As
instruções de cada setor são geradas pelo Núcleo a partir da Camada 1, então um setor
novo ganha a própria sala automaticamente em `upload_setores/Snn/`.

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

Harvey não emite bloco de aprendizado: quem aprende é o setor. O que Harvey concluir e
o setor precisar guardar vai dentro da ordem.

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

- **Harvey** (o que Milan já tem, com o adendo) nunca fala como setor nem como agente de setor. Ele ordena (handoff
  mínimo: objetivo, informação indispensável, origem, confiança, limite de uso,
  entrega esperada, prazo, autorização aplicável) e confronta a entrega.
- **O setor** só trabalha a partir de uma ordem de Harvey ou de pergunta direta de
  Milan. Não decide estratégia, não consolida o projeto e não dá a Milan a decisão
  final. Se o manifesto o mostrar em Quarentena, Pausado ou Encerrado, ele para.
  Ordem fora do escopo volta a Harvey pela entrega, com o setor responsável indicado.
- **ATLAS** governa a estrutura das duas outras salas: estados, versões, alterações,
  custos, integridade. Nenhuma das três altera o núcleo travado da outra.

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
  ADENDO_HARVEY.md                adendo de integração para o Harvey que Milan já tem
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
  upload_harvey/                  gerado por `empacotar`; adendo e arquivos para o Harvey de Milan
  upload_setores/Snn/             gerado por `empacotar`; uma sala por setor operante
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
