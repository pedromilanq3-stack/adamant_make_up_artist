# Tinder Web — mensagens assistidas (Tampermonkey)

## O que este script é e o que ele não é

`tinder-messages.user.js` é um assistente de preenchimento e envio de mensagens,
comparável a um autofill de formulário: ele **nunca** envia nada sozinho. Todo envio
real exige um clique explícito em **CONFIRMAR ENVIO**, item a item, dentro do próprio
painel. Ele não é um bot de disparo em massa.

Restrições de propósito, por desenho:

- Opera **somente na conta já autenticada no navegador do usuário**. Não cria contas,
  não gerencia múltiplas contas e não automatiza login.
- Não resolve, contorna nem tenta evitar CAPTCHA. Ao detectar qualquer sinal de
  CAPTCHA, verificação, bloqueio ou aviso de limite, ele **para imediatamente** e
  descarta os itens pendentes da fila.
- Não tenta contornar limites de taxa, restrições técnicas ou de conta do Tinder. O
  ritmo de envio é o ritmo do usuário clicando em "Preparar próximo" e depois
  "CONFIRMAR ENVIO" — não há disparo automático em sequência.
- Atua apenas sobre as conversas que o próprio usuário marcar manualmente na lista.
  Não varre nem envia para conversas fora da seleção.
- Tem um limite máximo de interações por sessão (padrão 50, configurável até 200),
  que zera apenas ao recarregar a página.
- Não coleta nem guarda dados pessoais além do necessário para a sessão: a fila e o
  log guardam somente o **nome exibido** na lista de conversas e o **texto da
  mensagem** que o próprio usuário escreveu/editou. Nada é lido do histórico da
  conversa, nem fotos, nem qualquer outro campo. Tudo fica em memória do navegador e
  some ao recarregar a página; a exportação (TXT/JSON) só acontece por ação do
  usuário.
- Não existe integração com nenhuma API oficial de mensagens do Tinder porque a
  plataforma não expõe uma API pública de envio para contas de usuário comum. Caso
  isso mude, a forma preferível passa a ser essa API, não a automação de DOM.

## Fluxo de uso

1. **Buscar conversas na tela** — lista as conversas atualmente visíveis na lista de
   matches do Tinder (role a lista manualmente para trazer mais itens antes de
   buscar novamente).
2. Marque as caixas de seleção das conversas desejadas.
3. Escreva a mensagem no campo de texto. `{nome}` é substituído pelo nome exibido de
   cada conversa selecionada.
4. Clique em **Adicionar selecionadas à fila**. Isso só grava a fila em memória; nada
   é enviado nesta etapa.
5. Clique em **Preparar próximo da fila**: o script abre a conversa, preenche o campo
   de mensagem do Tinder (sem clicar em enviar) e mostra o texto exato em
   "Preview".
6. Revise o texto. Clique em **CONFIRMAR ENVIO** para realmente enviar (ou deixe
   **Dry Run** marcado para só simular, sem clicar no botão de enviar real). Use
   **Pular** para descartar o item sem enviar.
7. O contador "Enviadas nesta sessão" impede novo processamento ao atingir o limite
   configurado.
8. **PARAR / limpar fila** interrompe tudo e descarta itens pendentes/preparados
   imediatamente; útil também como botão de emergência.

## Verificações de segurança antes de cada passo

O script confere sinais de CAPTCHA/bloqueio/aviso de limite:

- antes de buscar conversas;
- antes de montar a fila;
- antes de abrir cada conversa;
- **imediatamente antes de clicar em enviar**, depois da confirmação manual.

Qualquer sinal detectado interrompe o processamento e remove os itens ainda
pendentes ou preparados da fila. Itens já enviados permanecem no histórico local
apenas para consulta/exportação.

Antes do clique final, o script também relê o valor atual do campo de mensagem e
compara com o texto que ele mesmo preencheu. Se o conteúdo mudou (por exemplo, o
usuário editou o campo manualmente depois de preparado), o envio é cancelado e
registrado como `MISMATCH`, em vez de enviar algo diferente do que foi revisado.

## Instalação no Tampermonkey

1. Instale a extensão **Tampermonkey** pela loja oficial do Chrome ou Edge.
2. Abra o painel do Tampermonkey e escolha **Criar novo script**.
3. Apague o modelo, copie todo o conteúdo de `tinder-messages.user.js`, cole e salve.
4. Entre em `https://tinder.com/`. Um painel **Mensagens assistidas (local)** aparece
   no canto superior esquerdo (o painel do `tinder-bot.user.js`, se instalado, fica
   no canto oposto, e os dois podem coexistir).
5. Deixe **Dry Run** marcado na primeira execução.

## Teste seguro com Dry Run

1. Marque **Dry Run** e **DEBUG no console** (`F12` → Console).
2. Busque conversas, selecione 1, escreva uma mensagem de teste e adicione à fila.
3. Clique em **Preparar próximo da fila**, confira o preview e clique em
   **CONFIRMAR ENVIO**. O log deve mostrar `DRY_RUN` e nenhum clique real deve ter
   sido feito no botão de enviar do Tinder.
4. Exporte o log (TXT ou JSON) e confirme que ele só contém horário, ação, nome
   exibido, texto da mensagem e resultado — nada além disso.
5. Só depois desse teste, desmarque Dry Run e faça um ensaio supervisionado com
   limite baixo (por exemplo `1`) antes de aumentar o volume.

## Como atualizar seletores

A interface do Tinder muda com frequência. Se **Buscar conversas na tela** não
encontrar nada, ou o campo/botão de enviar não for localizado:

1. Pare o processamento e mantenha **Dry Run** ligado. Nunca investigue seletores
   com o Dry Run desligado.
2. Use o seletor de elementos do DevTools (`Ctrl+Shift+C`) no item de conversa, no
   campo de mensagem e no botão de enviar.
3. Prefira atributos estáveis: `data-testid`, `aria-label`, `role`. Evite classes
   CSS geradas dinamicamente.
4. Acrescente o novo seletor ao array correspondente em `CONFIG.selectors`
   (`conversationItems`, `conversationName`, `messageInput` ou `sendButton`),
   mantendo os seletores antigos como fallback.
5. Para avisos de segurança novos, adicione seletor a `safetySignals` ou expressão a
   `safetyText`, sempre preferindo falso positivo (parar) a continuar durante uma
   verificação real.
6. Salve, recarregue o Tinder e repita o teste Dry Run da seção anterior.

## Privacidade do log

O log e a fila existem só em memória, apenas enquanto a aba está aberta. Recarregar a
página apaga tudo. A exportação só ocorre por clique explícito do usuário e contém
apenas horário, ação, nome exibido (quando disponível na lista de conversas), texto
da mensagem preparada/enviada e resultado. Nenhuma foto, URL de imagem, cookie,
token ou credencial é lida ou registrada pelo script.
