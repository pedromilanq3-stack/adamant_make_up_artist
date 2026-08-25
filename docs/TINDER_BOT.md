# Tinder Web — assistente de decisões (Tampermonkey)

## Arquitetura e limites

`tinder-bot.user.js` é um userscript executado localmente no Firefox, Chrome ou Edge. Ele não
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

### Firefox: quando o projeto foi baixado como ZIP

O ZIP deste repositório **não é um pacote instalável do Tampermonkey**. Ele é apenas
uma pasta compactada com o código-fonte. Não use **Utilitários → Importar do arquivo**
com esse ZIP: essa opção é destinada a backups exportados pelo próprio Tampermonkey.

1. No Firefox, instale o complemento **Tampermonkey** pelo site oficial de
   complementos da Mozilla e confirme **Adicionar**.
2. Baixe o ZIP do projeto e extraia-o normalmente pelo Explorador de Arquivos,
   Finder ou gerenciador de arquivos. Entre na pasta extraída.
3. Abra `tinder-bot.user.js` em um editor de texto e copie todo o conteúdo
   (`Ctrl+A`, `Ctrl+C`). Não tente enviar o ZIP inteiro ao Tampermonkey.
4. No Firefox, clique no ícone do Tampermonkey → **Painel de controle** → botão `+`
   ou **Criar novo script**.
5. Apague o modelo do editor, cole o conteúdo copiado (`Ctrl+V`) e salve com
   `Ctrl+S`. Confirme no painel que o script está **Ativado**.
6. Abra ou recarregue `https://tinder.com/`. O painel **TinderBot (local)** deve
   aparecer no canto superior direito. Comece com **Dry Run** marcado.

Se o arquivo ZIP tiver sido criado por **Tampermonkey → Utilitários → Exportar**, aí
sim ele pode ser restaurado em **Painel de controle → Utilitários → Importar do
arquivo**. Antes de confirmar, revise a lista de scripts apresentada. Esse não é o
formato do ZIP comum baixado deste repositório.

Se o painel não aparecer, confira nesta ordem: o complemento e o script estão
ativados; a página aberta é exatamente `https://tinder.com/`; o Firefox não está em
uma janela privativa sem permissão para o complemento; e a página foi recarregada
depois de salvar o script.

### Firefox mostra “Parcialmente restrito” e “Nenhum script sendo executado”

Essas duas mensagens no menu do Tampermonkey significam que o userscript **não chegou
a ser executado**. Portanto, nesse caso o problema ainda não é o seletor do Tinder nem
a montagem do painel. Faça o seguinte:

1. Clique na linha amarela **Parcialmente restrito pelas configurações** e veja se o
   Firefox oferece uma permissão específica para `tinder.com`.
2. Se em `about:addons` → **Tampermonkey → Permissões e dados** já constar, na seção
   **Necessário**, **Acessar seus dados em todos os sites visitados**, a permissão de
   acesso ao Tinder já está concedida. Não é necessário habilitar proxy nem acesso a
   arquivos locais e não haverá necessariamente uma opção chamada “Executar scripts
   de usuário”. Nesse cenário, prossiga para conferir a instalação do script.
3. Volte ao **Painel de controle** do Tampermonkey e confirme que **Tinder Web -
   Assistente de decisões** consta na lista e que sua chave está ativada. Se ele não
   estiver na lista, o código apenas foi aberto, mas não foi salvo/instalado.
4. Abra o editor do script e confirme que o cabeçalho ainda contém
   `@match https://tinder.com/*`. Não copie marcadores de conflito do GitHub.
5. Volte à aba do Tinder e faça uma recarga completa com `Ctrl+F5`. Abra novamente o
   menu do Tampermonkey: ele deve listar **Tinder Web - Assistente de decisões** em vez
   de **Nenhum script sendo executado**.

Para isolar uma instalação incompleta, abra **Adicionar novo script**, apague o modelo,
cole o arquivo `tinder-bot.user.js` inteiro — desde `// ==UserScript==` até o último
`})();` — e pressione `Ctrl+S`. Não cole apenas a parte interna da função. Se o editor
mostrar erro de sintaxe, procure e remova marcadores `<<<<<<<`, `=======` e `>>>>>>>`;
eles pertencem à tela de conflitos do GitHub e não são JavaScript válido.

Mantenha **somente uma cópia** do TinderBot. Se o painel listar várias linhas com o
mesmo nome, use a lixeira para apagar as versões antigas e preserve apenas a de maior
versão (atualmente `1.3.2`), ativada. Várias cópias podem criar timers e observadores
concorrentes na mesma aba, ainda que o script tenha uma trava de instância.

Observe também se a janela exibe **Navegação privativa**. Em uma janela privativa, abra
`about:addons` → **Tampermonkey → Detalhes** e permita a execução em janelas
privativas, ou faça o teste em uma janela normal do Firefox. A permissão de navegação
privativa fica em **Detalhes** e pode não aparecer na aba **Permissões e dados**.

Não altere opções avançadas de segurança do Firefox além das permissões específicas
do Tampermonkey e do domínio `tinder.com`. Se o navegador for administrado por uma
empresa/escola e a permissão estiver bloqueada por política, use um perfil pessoal
administrado por você; o script não tenta contornar políticas do navegador.

Na versão 1.3.2 ou posterior, recupere o painel sem reinstalar pressionando
**Alt+Shift+T** na aba do Tinder.

O painel agora é anexado ao elemento raiz do documento, em vez do `body`, porque o
Tinder pode substituir o `body` durante uma navegação SPA. O script também verifica a
cada segundo se o painel foi removido e o recria automaticamente. Ao atualizar o
código no editor do Tampermonkey, salve e faça uma recarga completa com `Ctrl+F5`.

O cabeçalho usa `@grant none` para manter o modo de execução mais simples e compatível
com o Tampermonkey no Firefox. Por isso, a versão 1.3.2 não depende de comandos extras
no menu da extensão; o botão **PARAR / EMERGÊNCIA** continua disponível no painel.

Se o painel aparecer como **ATIVO**, mas o total continuar em zero, substitua o código
instalado pela versão atual deste repositório e recarregue a página. A versão atual
também encontra variantes do Tinder que não possuem `data-testid="profile-card"`:
ela localiza os botões ❤️/X e sobe pela árvore DOM até o contêiner que contém o nome.
Na versão 1.3.2, o nome e a idade também podem ser identificados em texto comum quando
o Tinder não usa mais elementos `h1`/`h2`; esse texto serve apenas para sincronizar o
card e nunca é usado para inferir gênero.
Como último fallback para os controles, a versão 1.3.2 reconhece estruturalmente o
gamepad somente quando encontra exatamente cinco botões circulares visíveis no mesmo
contêiner (desfazer, X, estrela, coração e boost). Ela usa a ordem DOM desse grupo, não
coordenadas fixas; seletores semânticos continuam tendo prioridade.
O botão de desfazer pode estar desabilitado e ainda participa da identificação dos
cinco controles; somente o alvo X/coração precisa estar habilitado antes da ação.
Para esperar o próximo perfil, a identidade textual nome+idade da região principal tem
prioridade sobre títulos estáticos e cards antigos mantidos no DOM pela animação. Isso
evita ficar em **AGUARDANDO novo perfil** quando o perfil visível já mudou.
Ative **DEBUG no console** antes de iniciar. O status **AGUARDANDO perfil/botões**
significa que nem o card nem os controles semânticos foram encontrados; nesse caso,
siga o procedimento de atualização de seletores abaixo e não faça cliques automáticos.

### Chrome e Edge (ou instalação manual equivalente)

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
