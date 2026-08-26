# Sexlog — mensagens assistidas (Tampermonkey)

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

1. Instale a extensão **Tampermonkey** pela loja oficial do Chrome ou Edge.
2. Abra o painel do Tampermonkey e escolha **Criar novo script**.
3. Apague o modelo, copie todo o conteúdo de `sexlog-messages.user.js`, cole e salve.
4. Entre em `https://www.sexlog.com/`. Um painel **Mensagens assistidas — Sexlog
   (local)** aparece no canto superior esquerdo, com um aviso de que os seletores
   ainda não foram confirmados.
5. **Não desmarque Dry Run** antes de completar a validação de seletores abaixo.

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
