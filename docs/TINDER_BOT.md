# Tinder Web — assistente de decisões (Tampermonkey)

## Arquitetura e limites

`tinder-bot.user.js` é um userscript executado localmente no Chrome ou Edge. Ele não
usa fotos, visão computacional, reconhecimento facial, rede externa, credenciais,
CAPTCHA ou mecanismos de evasão. Há dois modos:

1. **Perfis já filtrados pelo Tinder:** trata todo card apresentado como aceito pelo
   filtro que o próprio usuário configurou e escolhe `LIKE`.
2. **Regra por texto explícito:** procura apenas declarações textuais inequívocas no
   DOM (por exemplo, `Gênero: mulher`). Mulher resulta em `LIKE`, homem em `REJECT` e
   ausência/ambiguidade em `SKIP`, sem clique.

O fluxo é dividido nas funções pedidas: `getCurrentProfile`, `getExplicitGender`,
`findLikeButton`, `findRejectButton`, `decideAction`, `performAction`,
`waitForNextProfile`, `startAutomation`, `stopAutomation`, `updateUI` e `writeLog`.
Os seletores, rótulos, padrões explícitos, avisos de segurança e valores padrão estão
centralizados em `CONFIG` no início do arquivo.

Um `MutationObserver` reage a mudanças do DOM. Uma impressão derivada somente do
texto/nome/atributos do card identifica o perfil atual (URLs e imagens não entram na
impressão). Antes do clique, o código confere visibilidade, estado habilitado e se a
impressão ainda é a mesma. Depois, aguarda uma impressão realmente diferente.
`processing`, `lastHandledFingerprint` e a nova validação imediatamente anterior ao
clique formam as três travas contra corrida/clique duplo. Um monitor leve de URL
reinstala o observador após navegação SPA e recria o painel caso o Tinder remova o nó.

> Automação pode contrariar termos ou limites da plataforma. Use por sua conta, com
> limite baixo, supervisão e Dry Run primeiro. O script para ao detectar CAPTCHA,
> verificação, atividade suspeita ou bloqueio; ele não tenta contornar esses controles.

## Instalação no Tampermonkey

1. Instale a extensão **Tampermonkey** pela loja oficial do Chrome ou Edge.
2. Abra o painel do Tampermonkey e escolha **Criar novo script**.
3. Apague o modelo, copie todo o conteúdo de `tinder-bot.user.js`, cole e salve.
4. Entre em `https://tinder.com/`. Um painel **TinderBot (local)** aparecerá no canto
   superior direito.
5. Configure no Tinder quem deseja ver. No painel, selecione o modo, limite e atrasos.
   O atraso mínimo aceito é 500 ms; recomenda-se manter valores bem maiores.
6. Deixe **Dry Run** ligado na primeira execução e clique **INICIAR**.

O botão **PARAR / EMERGÊNCIA** cancela novos passos. Um clique já despachado pelo
navegador não pode ser desfeito pelo script. Recarregar a página também encerra a
execução e restaura contadores/logs, que existem apenas em memória.

## Teste seguro com Dry Run

1. Abra as DevTools (`F12`), aba **Console**, e marque **DEBUG no console**.
2. Marque **Dry Run**, use limite `3` e escolha o modo desejado.
3. Clique **INICIAR**. Confira status, decisão e log; nenhum botão deve ser clicado.
4. Como o card não muda sozinho no Dry Run, avance manualmente. O observador deverá
   detectar o card seguinte e analisá-lo uma única vez.
5. Exporte TXT e JSON e confirme horário, ação pretendida, motivo, nome somente se
   exposto na interface e resultado `Dry Run: clique não executado`.
6. Somente depois desse teste, desmarque Dry Run e faça um ensaio supervisionado com
   limite `1`. Pare imediatamente diante de comportamento inesperado.

No modo textual, um card sem texto inequívoco deve ficar em **INDETERMINADO — avance
manualmente**, nunca sendo decidido pela foto.

## Como descobrir e atualizar seletores

1. **Pare o robô e ative Dry Run.** Nunca investigue seletores com cliques automáticos.
2. Abra DevTools (`F12`) e use o seletor de elementos (`Ctrl+Shift+C`). Selecione o
   botão de coração, o botão X, o card e o nome.
3. Prefira atributos estáveis e semânticos: `data-testid`, `aria-label`, `title`,
   `role`. Evite classes CSS geradas e coordenadas. No Console, valide algo como:
   `document.querySelector('button[aria-label="Like"]')` e confira se retorna
   exatamente o botão visível.
4. Acrescente o seletor ao array apropriado em `CONFIG.selectors`:
   `profileCards`, `profileName`, `likeButtons` ou `rejectButtons`. Coloque o mais
   específico primeiro e preserve os fallbacks existentes.
5. Se o idioma mudou, acrescente o rótulo exato a `semanticLabels`. Só altere
   `explicitGender` para formatos que realmente declarem gênero; nunca inclua nomes,
   pronomes isolados, aparência ou qualquer sinal visual.
6. Para telas de segurança novas, acrescente seletor a `safetySignals` ou expressão a
   `safetyText`, preferindo falso positivo (parar) a continuar durante verificação.
7. Salve, recarregue o Tinder, faça novamente o teste Dry Run com DEBUG e limite 3.

Mensagens esperadas no Console incluem `Perfil detectado`, `Decisão: LIKE`, `Botão
encontrado`, `Clique realizado` e `Aguardando próximo perfil`, todas prefixadas por
`[TinderBot]`.

## Revisão de concorrência e falhas

- `processing` impede duas execuções simultâneas disparadas pelo observador.
- O fingerprint é conferido novamente depois do atraso e imediatamente antes do
  clique, evitando clicar no card substituído.
- `lastHandledFingerprint` impede repetição no mesmo card, inclusive em Dry Run e em
  erros de botão. Em `SKIP`, o avanço fica deliberadamente manual.
- Após clique bem-sucedido, `waitForNextProfile` exige mudança real. Timeout apenas
  registra a falha; não repete o clique.
- `stopRequested` é verificado após cada espera. O botão de emergência desconecta o
  observador e cancela o timer pendente.
- O contador registra decisões processadas; em Dry Run, ❤️/X são intenções, e o campo
  `result` deixa explícito que nenhum clique ocorreu.
- Exceções são registradas e o perfil recebe trava de repetição, privilegiando não
  clicar duas vezes.

## Privacidade do log

O log fica em memória até recarregar a página. A exportação só acontece por ação do
usuário e contém horário, ação, razão, resultado, fingerprint textual e nome quando o
nome já está disponível no card. Fotos, URLs de fotos, cookies e credenciais nunca são
lidos nem gravados pelo script.
