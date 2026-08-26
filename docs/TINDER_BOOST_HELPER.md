# Tinder Boost Helper

Userscript para detectar e ativar **somente um Boost que a própria interface oficial
do Tinder apresente como disponível**. Ele interrompe o fluxo ao identificar preço,
compra, upgrade, CAPTCHA ou aviso de segurança.

## Instalação

1. Instale Tampermonkey ou outro gerenciador compatível com userscripts.
2. Crie um script novo e cole o conteúdo de `tinder-boost-helper.user.js`.
3. Salve e abra `https://tinder.com/`.
4. Use **VERIFICAR** antes de tentar **ATIVAR BOOST**.

## Alternativa sem contornar o sistema

Não existe uma ação local legítima que transforme a conta em “primeiro dia” ou
reponha um benefício controlado pelos servidores. Como alternativa, use **AVISAR
QUANDO LIBERAR**: enquanto a aba do Tinder permanecer aberta, o helper verifica a
interface oficial a cada minuto e envia uma notificação quando ela passar a indicar
um Boost disponível. O aviso não ativa, compra ou cria o benefício.

Se a renovação prevista não aparecer, confira a assinatura e a restauração de
compras nas opções oficiais da conta ou procure o suporte do Tinder. Não forneça
cookies, tokens, senha ou código de verificação a scripts ou terceiros.

### O único “reset” local útil

**RECARREGAR ESTADO OFICIAL** recarrega a página e faz o site consultar novamente
o estado atual da conta. Isso pode corrigir apenas uma interface desatualizada — por
exemplo, quando o servidor já liberou o benefício, mas a aba antiga ainda não o
mostrou. O botão não antecipa renovação e não muda o saldo no servidor.

Limpar cookies, trocar o relógio, reinstalar o userscript, criar requisições ou
alterar valores no navegador também não repõe um Boost controlado pelo servidor.
Não foi implementada qualquer tentativa de falsificar saldo ou burlar assinatura.

## Histórico e “reset”

Quando a página confirma uma ativação, o script guarda no armazenamento do
userscript a data local. A estimativa de 30 dias é apenas informativa: não é a data
oficial de renovação da conta.

**APAGAR HISTÓRICO LOCAL** remove somente essa data do navegador. Essa ação não
reinicia contagem, libera Boost, cria saldo, altera assinatura nem modifica dados
nos servidores do Tinder. Saldo e renovação só podem ser administrados pelos meios
oficiais oferecidos na conta.

## Limitações de segurança

- A interface do Tinder pode mudar; por isso o script exige um único controle de
  entrada e uma confirmação com texto explícito.
- Se houver mais de um candidato ou o texto for ambíguo, nenhum clique é feito.
- O script não tenta resolver CAPTCHA, contornar paywall ou automatizar pagamento.
- O monitor funciona somente com a aba aberta e depende do texto exibido pelo Tinder.
- Confirme sempre o estado final diretamente na interface oficial.
