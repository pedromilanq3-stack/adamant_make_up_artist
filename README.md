# Gateway GPT → Meta Ads

Este projeto permite que um GPT **consulte e altere campanhas** da conta de anúncios
`934861699094739` usando a **Meta Marketing API oficial**. Ele não automatiza cliques
nem entrega a senha do Facebook ao modelo: o token fica somente no servidor.

> A URL do Ads Manager informada aponta para a campanha `52564925569669`. Esses IDs
> não são credenciais; ainda é necessário criar um app/token autorizado na Meta.

## Proteções incluídas

- conta de anúncios permitida por variável de ambiente;
- campos editáveis limitados a nome, status e orçamento;
- somente `ACTIVE` e `PAUSED` são aceitos como status;
- fluxo obrigatório em duas etapas: **preview** e **apply**;
- confirmação assinada, vinculada exatamente às alterações e válida por 5 minutos;
- token da Meta nunca aparece no OpenAPI nem nas respostas.
- todos os endpoints operacionais exigem uma `X-API-Key` separada.

## Configuração

1. No Meta for Developers/Business Manager, crie um app empresarial e um usuário do
   sistema com acesso somente aos ativos necessários. Gere um token com as permissões
   adequadas (normalmente `ads_read` para leitura e `ads_management` para alteração).
2. Copie `.env.example` para `.env`, informe o token, uma versão suportada da Graph API
   e um segredo aleatório. Não use token pessoal de curta duração em produção.
3. Instale e execute:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
set -a; . ./.env; set +a
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

A documentação interativa ficará em `http://localhost:8000/docs` e o schema para uma
Action em `http://localhost:8000/openapi.json`.

## Conectar a um GPT

1. Publique este serviço atrás de **HTTPS**; mantenha também rate limit no reverse proxy.
2. No editor do GPT, crie uma Action e importe `https://SEU-DOMINIO/openapi.json`.
   Configure autenticação por API key, cabeçalho `X-API-Key`, usando o valor de
   `GATEWAY_API_KEY`.
3. Nas instruções do GPT, determine: “Sempre chame `previewCampaignChanges`, mostre
   `current` e `changes`, peça confirmação explícita e somente então chame
   `applyCampaignChanges` com o mesmo conteúdo e `confirmation_token`.”
4. Teste primeiro com uma campanha pausada e orçamento baixo.

Exemplo manual:

```bash
curl -sS -X POST http://localhost:8000/campaigns/52564925569669/preview \
  -H "X-API-Key: $GATEWAY_API_KEY" \
  -H 'content-type: application/json' \
  -d '{"status":"PAUSED"}'
```

Depois da confirmação humana, envie o token retornado para `/apply`, repetindo
exatamente as mesmas alterações.

## Limites atuais

Este MVP atua no nível de **campanha**. Conjuntos de anúncios, anúncios/criativos,
segmentação e relatórios devem ser adicionados como operações separadas, com validação
e confirmação próprias. Antes de produção, adicione autenticação externa, rate limit,
logs de auditoria sem segredos, rotação de token e armazenamento seguro de segredos.

Não é recomendável usar Playwright/Selenium para “entrar” no Ads Manager: login com
MFA, mudanças de interface e checkpoints tornam essa via frágil. A API oficial é mais
auditável e não exige compartilhar login ou cookies com o GPT.
