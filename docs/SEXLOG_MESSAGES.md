# Sexlog — mensagens assistidas (Tampermonkey)

## O que já foi confirmado por print de tela

- O campo de mensagem tem o placeholder **"Digite sua mensagem"** — o script já
  procura por `input[placeholder="Digite sua mensagem"]` primeiro.
- O botão de enviar é só um **ícone de seta**, sem texto ou rótulo visível. Não dá
  para mirar nele por texto/aria-label com segurança, então o script usa um
  fallback estrutural (`locateSendButton` em `sexlog-messages.user.js`): procura o
  último elemento clicável visível dentro do mesmo `<form>` (ou contêiner) do campo
  de mensagem — que costuma ser exatamente esse botão de seta, já que ele fica à
  direita do campo na interface.
- Ainda não sabemos o atributo real do botão (`class`, `aria-label`, `data-*`), então
  esse fallback é uma aposta razoável, não uma confirmação. Teste sempre com Dry Run
  antes de confiar nele.

## Detecção automática (melhor esforço)

A pedido do usuário, o script não depende de seletores confirmados manualmente: ele
tenta descobrir sozinho o campo de mensagem e o botão de enviar, usando várias
tentativas em cascata (`CONFIG.selectors`) e, para o botão (que é só um ícone sem
texto), um fallback estrutural (`locateSendButton`) que procura o elemento clicável
mais próximo do campo, começando pela linha imediata e só alargando a busca se
necessário. Isso é conveniente, mas continua sendo uma aposta, não uma garantia —
por isso o **Dry Run é obrigatório** na primeira execução em qualquer conta: confira
no preview do painel se o texto realmente foi parar no campo certo antes de desmarcar
Dry Run e confirmar um envio de verdade.

## Aviso importante: seletores não confirmados

Diferente do assistente para Tinder Web deste repositório, a estrutura de página do
Sexlog **não é conhecida** por quem escreveu este script. `CONFIG.selectors` em
`sexlog-messages.user.js` é um ponto de partida genérico (padrões comuns como
`textarea`, `button[type="submit"]`, links contendo `/mensagens/`), não uma lista
validada. **Não desligue o Dry Run até confirmar, com o DevTools aberto, que cada
seletor aponta exatamente para o elemento certo.** Veja a seção "Como descobrir e
ajustar seletores" abaixo antes de qualquer envio real.

## O que este script é e o que ele não é

`sexlog-messages.user.js` é um assistente de preenchimento e envio de mensagens,
comparável a um autofill de formulário: ele **nunca** envia nada sozinho. Todo envio
real exige um clique explícito em **CONFIRMAR ENVIO**, item a item, dentro do próprio
painel. Ele não é um bot de disparo em massa.

Restrições de propósito, por desenho (as mesmas do assistente do Tinder):

- Opera **somente na conta já autenticada no navegador do usuário**. Não cria contas,
  não gerencia múltiplas contas e não automatiza login.
- Não resolve, contorna nem tenta evitar CAPTCHA. Ao detectar qualquer sinal de
  CAPTCHA, verificação, bloqueio/suspensão de conta ou aviso de limite, ele **para
  imediatamente** e descarta os itens pendentes da fila.
- Não tenta contornar limites de taxa, restrições técnicas ou de conta do Sexlog. O
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
- Não há integração com nenhuma API oficial de mensagens do Sexlog porque a
  plataforma não expõe uma API pública documentada para contas de usuário comum, até
  onde se sabe. Se isso existir ou mudar, a forma preferível passa a ser essa API, não
  a automação de DOM.

## Instalação no Tampermonkey

Tampermonkey não roda em Chrome/Safari de celular. No Android, use **Kiwi Browser**
(aceita extensões Chrome, inclusive Tampermonkey) ou **Firefox para Android** com o
addon Tampermonkey.

1. Instale a extensão **Tampermonkey** no navegador escolhido.
2. Abra o painel do Tampermonkey e escolha **Criar novo script**.
3. Apague o modelo, copie todo o conteúdo de `sexlog-messages.user.js`, cole e salve.
4. Entre em `https://www.sexlog.com/`. Um painel **Mensagens assistidas — Sexlog
   (local)** aparece no canto superior esquerdo, com um aviso de que os seletores
   ainda não foram confirmados.
5. **Não desmarque Dry Run** antes de completar a validação de seletores abaixo.

### Conferir o HTML pelo celular, sem instalar nada

Chrome e a maioria dos navegadores mobile aceitam abrir a versão "código-fonte" de
uma página com o prefixo `view-source:` na barra de endereço (ex.:
`view-source:https://www.sexlog.com/ultimate-mensagens/<usuário>`). Isso mostra o
HTML como texto puro. Use o "Localizar na página" do menu do navegador para buscar
por `Digite sua mensagem` e veja o trecho ao redor — ele mostra a tag exata do campo
(`input` ou `textarea`) e, principalmente, algum atributo do botão de enviar
(`class`, `aria-label`, `data-*`) que hoje o script só está adivinhando. Como essa
página parece ser renderizada pelo servidor (não uma SPA), o `view-source:` deve
mostrar o mesmo HTML que o navegador realmente usa.

## Como descobrir e ajustar seletores (faça isto primeiro)

1. Com o script instalado e **Dry Run marcado**, navegue até
   `https://www.sexlog.com/ultimate-mensagens` (área de mensagens da sua conta) e
   abra uma conversa existente. O ambiente usado para escrever este script não
   conseguiu acessar esse domínio (bloqueio de rede do lado da automação, além de a
   página exigir login), então os seletores abaixo continuam não confirmados até
   alguém validar com a própria conta.
2. Abra o DevTools (`F12`) e use o seletor de elementos (`Ctrl+Shift+C`) em três
   coisas: (a) o link/item de cada conversa na lista, (b) o campo onde se digita a
   mensagem, (c) o botão que efetivamente envia.
3. Prefira atributos estáveis: `data-testid`, `name`, `aria-label`, `id`. Evite
   classes CSS geradas dinamicamente (ex.: hashes tipo `css-x92j1`).
4. Abra `sexlog-messages.user.js` no editor do Tampermonkey e ajuste
   `CONFIG.selectors`:
   - `conversationItems`: seletor(es) que localizam cada item clicável da lista de
     conversas.
   - `conversationName`: onde fica o nome exibido dentro de cada item.
   - `messageInput`: o campo de texto da mensagem (textarea ou `contenteditable`).
   - `sendButton`: o botão de enviar da conversa aberta.
   Coloque o seletor mais específico primeiro; os genéricos atuais podem ficar como
   último fallback, ou ser removidos se causarem falsos positivos.
5. Para telas de segurança do Sexlog (verificação, aviso de conta, limite atingido),
   adicione seletor a `safetySignals` ou expressão a `safetyText`, sempre preferindo
   falso positivo (parar) a continuar durante uma verificação real.
6. Salve, recarregue a página e repita o teste Dry Run da seção seguinte até os
   seletores baterem certinho.

## Teste seguro com Dry Run

1. Marque **Dry Run** e **DEBUG no console** (`F12` → Console).
2. Clique em **Buscar conversas na tela** e confira se os nomes listados batem com
   as conversas reais visíveis. Se a lista vier vazia ou errada, volte para a seção
   de seletores.
3. Selecione 1 conversa de teste, escreva uma mensagem de teste e adicione à fila.
4. Clique em **Preparar próximo da fila** e confirme, olhando a própria página, que o
   campo de mensagem da conversa foi preenchido com o texto certo — sem nenhum clique
   de envio real.
5. Clique em **CONFIRMAR ENVIO**. O log deve mostrar `DRY_RUN` e nenhuma mensagem deve
   ter sido efetivamente enviada no Sexlog.
6. Exporte o log (TXT ou JSON) e confirme que ele só contém horário, ação, nome
   exibido, texto da mensagem e resultado — nada além disso.
7. Só depois de validar os seletores e repetir esse teste com sucesso, desmarque Dry
   Run e faça um ensaio supervisionado com limite baixo (por exemplo `1`) antes de
   aumentar o volume.

## Verificações de segurança antes de cada passo

O script confere sinais de CAPTCHA/bloqueio/suspensão/aviso de limite:

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

## Privacidade do log

O log e a fila existem só em memória, apenas enquanto a aba está aberta. Recarregar a
página apaga tudo. A exportação só ocorre por clique explícito do usuário e contém
apenas horário, ação, nome exibido (quando disponível na lista de conversas), texto
da mensagem preparada/enviada e resultado. Nenhuma foto, URL de imagem, cookie,
token ou credencial é lida ou registrada pelo script.
