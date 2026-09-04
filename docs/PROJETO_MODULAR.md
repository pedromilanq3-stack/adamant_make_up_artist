# Projeto Modular de Decisão e Reconstrução — o cérebro que evolui dentro do GPT

Este é o sistema descrito no documento fundador de Milan: Harvey Specter como
interface, o Núcleo Central de Coordenação, o Setor 01 — Rota de Renda com seus cinco
agentes, e um cérebro em cinco camadas por setor. Ele foi feito para rodar em um
**Projeto do ChatGPT** (ecossistema GPT/OpenAI) e para **evoluir sem se corromper**:
aprende com resultados, se adapta quando fatos vencem, corrige os próprios erros
preservando o histórico, e cresce por novos setores sem que um setor altere outro.

Duas partes trabalham juntas:

| Parte | Onde vive | Papel |
|---|---|---|
| `gpt_projeto/` | no Projeto do ChatGPT (instruções + arquivos) | o cérebro que o GPT lê a cada conversa |
| `nucleo/` | no computador de Milan (`python -m nucleo`) | o guardião que aplica o aprendizado, valida, isola e regenera os arquivos |

O GPT não consegue editar os próprios arquivos. Por isso a evolução acontece num
ciclo curto: o GPT **propõe** (bloco de aprendizado), o Núcleo **aplica** com regras
duras, Milan **reenvia** os arquivos. Tudo o que é reservado a Milan exige a flag
`--autorizado-por-milan`; sem ela o Núcleo recusa.

## 1. Instalar o cérebro no ChatGPT (primeira vez)

Requer apenas os arquivos de `gpt_projeto/upload/` (já gerados neste repositório).

1. No ChatGPT, crie um **Projeto** chamado, por exemplo, "Reconstrução".
2. Em **Instruções** do Projeto, cole o conteúdo inteiro de
   `gpt_projeto/upload/00_INSTRUCOES_DO_PROJETO.md` (cabe no limite do campo; o
   comando `validar` avisa se passar de 8.000 caracteres).
3. Em **Arquivos** do Projeto, envie todos os outros arquivos de `upload/`:
   `01_PROTOCOLO_DO_CEREBRO.md`, `02_MANIFESTO.md`, `S01_ROTA_DE_RENDA.md` e, quando
   existir, `90_DOSSIES.md`.
4. Se o Projeto oferecer "memória só do projeto", ative. Isso ajuda, mas a memória
   oficial continua sendo os arquivos.
5. Abra uma conversa e diga "iniciar". Harvey ativa o Setor 01 com o RAIO-X e faz
   somente a pergunta de inicialização: "No seu último emprego, o que você fazia no
   dia a dia?".

## 2. O ciclo de evolução (a cada conversa que ensina algo)

```
1. conversar          Harvey responde; se algo mudou, termina com ```aprendizado```
2. copiar             copie a resposta inteira (ou só o bloco) para um arquivo, ex.: bloco.md
3. aplicar            python -m nucleo aplicar bloco.md
4. empacotar          python -m nucleo empacotar
5. reenviar           substitua no Projeto os arquivos de gpt_projeto/upload/ que mudaram
```

O comando `aplicar` aceita a resposta inteira do GPT: ele encontra os blocos
```` ```aprendizado ```` sozinho. Ele:

- atribui os ids (F-, H-, L-, D-); o GPT nunca inventa ids;
- recusa bloco cujo `setor:` não seja o único setor escrito;
- recusa fato de outro setor sem dossiê autorizado;
- recusa qualquer tentativa de tocar na Camada 1;
- recusa hipótese sem teste, prazo de revisão e condição de abandono;
- em correção, acrescenta o registro novo e marca o antigo como superado, apontando
  um para o outro;
- se qualquer seção do bloco estiver errada, não grava nada.

Sem Python à mão, o mesmo pode ser feito à mão: os arquivos em
`gpt_projeto/setores/S01_rota_de_renda/` usam o mesmo formato `## ID` + `- chave: valor`
do bloco. Depois, `validar` confere.

## 3. Comandos do Núcleo

```bash
python -m nucleo validar                 # camadas, travas, dossiês
python -m nucleo estado [S01]            # estado atual + pendências
python -m nucleo aplicar bloco.md        # ou: cat resposta.md | python -m nucleo aplicar
python -m nucleo empacotar               # regenera gpt_projeto/upload/
python -m nucleo revisar                 # fatos voláteis vencidos, hipóteses a revisar, prazos, autorizações
python -m nucleo metricas                # contadores de evolução e calibração por setor

python -m nucleo travar S01 --autorizado-por-milan        # depois de Milan editar a Camada 1
python -m nucleo setor listar
python -m nucleo setor propor S02 --carta carta.md         # Proposto (não opera)
python -m nucleo setor aprovar S02 --autorizado-por-milan  # cria as cinco camadas a partir da carta
python -m nucleo setor piloto  S02 --autorizado-por-milan
python -m nucleo setor ativar  S02 --autorizado-por-milan
python -m nucleo setor pausar | reativar | encerrar S02 --autorizado-por-milan
python -m nucleo dossie listar
python -m nucleo dossie autorizar D-001 --autorizado-por-milan
python -m nucleo dossie recusar   D-001 --autorizado-por-milan
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

**Não se corrompe.** A Camada 1 de cada setor é protegida por hash SHA-256 no
manifesto. Alteração sem `travar --autorizado-por-milan` faz `validar` falhar e
bloqueia `aplicar` e `empacotar` até Milan resolver. O manifesto enviado ao Projeto
traz os hashes, para o GPT perceber arquivo desatualizado.

## 5. Estrutura de arquivos

```
gpt_projeto/
  INSTRUCOES_DO_PROJETO.md        cola-se nas Instruções do Projeto
  PROTOCOLO_DO_CEREBRO.md         formato dos registros e do bloco de aprendizado
  manifesto.json                  setores, status, histórico, hash da Camada 1
  setores/S01_rota_de_renda/
    camada1_nucleo.md             travada: missão, limites, método, agentes
    camada2_fatos.md              F-nnn
    camada3_hipoteses.md          H-nnn
    camada4_licoes.md             L-nnn
    camada5_estado.md             ESTADO
  dossies/dossies.md              D-nnn (criado no primeiro dossiê)
  modelos/                        carta de setor e bloco de aprendizado em branco
  upload/                         gerado por `empacotar`; é o que vai ao Projeto
nucleo/                           o utilitário (Python 3.11+, sem dependências)
tests/test_nucleo.py              cobertura de parsing, isolamento, correção, dossiês, ciclo de vida, CLI
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
