---
name: openai-developers
description: Ajuda a desenvolver com produtos, APIs e SDKs da OpenAI a partir do Claude. Use para consultar documentação, escolher ou migrar modelos, melhorar prompts de API, configurar OPENAI_API_KEY com segurança, diagnosticar erros da API, construir agentes com OpenAI Agents SDK, criar ChatGPT Apps com Apps SDK e MCP ou preparar chatgpt-app-submission.json. Não ativar para um pedido genérico de IA que não envolva OpenAI, nem trocar o provedor escolhido pelo usuário.
---

# OpenAI Developers

Transformar pedidos sobre desenvolvimento com OpenAI em orientação fundamentada, código ou arquivos verificáveis. Responder no idioma do usuário. Esta skill reúne os seis módulos do pacote fornecido; as referências técnicas mantêm o inglês original com adaptações de compatibilidade.

## Ambiente e precedência

- Usar apenas ferramentas realmente disponíveis. A importação desta skill fornece instruções; não instala o servidor MCP, SDKs, conectores, acesso à conta ou chaves de API.
- No Claude.ai, distinguir os arquivos e o ambiente de execução da conversa do computador do usuário. Sem acesso explícito, não afirmar que leu ou alterou o projeto, terminal, variáveis de ambiente ou arquivos locais do usuário.
- Usar o OpenAI Docs MCP se estiver conectado. Caso contrário, consultar as páginas oficiais com pesquisa/navegação disponível. Sem ambos, trabalhar com o material fornecido e declarar quais informações atuais não foi possível verificar.
- A falta de chave bloqueia somente chamadas reais à API. Continuar documentação, planejamento, código, edições solicitadas e validação offline. Esta regra resolve o conflito entre o gate de credenciais e o módulo de documentação do pacote original.
- Respeitar o provedor e modelo explicitamente escolhidos. Reutilizar autorizações já dadas na conversa; confirmar somente decisões necessárias ainda não resolvidas ou ações fora do escopo autorizado.
- Tratar publicação, envio para revisão, compras e alterações externas como ações distintas da preparação de arquivos. A skill, por si só, não concede autorização para executá-las.

## Escolher a referência

Ler somente os módulos necessários. Os nomes abaixo identificam arquivos internos, sem dependência de outras skills instaladas.

| Pedido | Referência |
| --- | --- |
| Documentação, API, modelos, parâmetros, preços, migração ou prompts | [openai-docs.md](references/openai-docs.md) |
| Chave de API, variável OPENAI_API_KEY ou autenticação antes de uma chamada real | [openai-platform-api-key.md](references/openai-platform-api-key.md) |
| Erros de rede, 401, 403, 404, 429, quota ou rate limit | [openai-api-troubleshooting.md](references/openai-api-troubleshooting.md) |
| Construir, adaptar ou avaliar agentes com OpenAI Agents SDK | [agents-sdk.md](references/agents-sdk.md) |
| Construir ChatGPT App, servidor MCP ou widget com Apps SDK | [build-chatgpt-app.md](references/build-chatgpt-app.md) |
| Revisar app para submissão e gerar o arquivo de importação | [chatgpt-app-submission.md](references/chatgpt-app-submission.md) |

## Executar e entregar

1. Identificar a tarefa e aproveitar o contexto fornecido. Inspecionar arquivos relevantes quando estiverem acessíveis; pedir somente o material que faltar para avançar.
2. Verificar informações variáveis nas fontes oficiais antes de recomendar modelos, parâmetros ou requisitos de submissão. Preservar o alvo explícito; não substituir pelo modelo mais recente por iniciativa própria.
3. Consultar a referência escolhida e produzir o menor resultado completo que resolva o pedido. Para uma implementação, seguir a linguagem e convenções do projeto.
4. Antes de uma chamada real, seguir o módulo de credenciais. Nunca pedir que o usuário cole uma chave na conversa, nem incorporá-la em código, relatórios ou arquivos compartilhados.
5. Validar com os recursos disponíveis. Distinguir inspeção estática, testes offline, chamadas reais e etapas não executadas. Não apresentar testes planejados como resultados observados.
6. Entregar o resultado, como usar e apenas limitações relevantes. Citar páginas efetivamente consultadas para afirmações atuais. Para erros, informar classe provável, evidência e próxima ação.

## Exemplos de aplicação

- “Meu script voltou 429 insufficient_quota.” → Diagnosticar quota/créditos, distinguindo de limitação de frequência.
- “Migre este projeto para o modelo X.” → Consultar a documentação do modelo X, preservar comportamento e testar offline mesmo sem chave.
- “Crie um agente em Python usando OpenAI Agents SDK.” → Definir contrato e entregar implementação mínima; verificar credenciais apenas antes de executá-la contra a API.
- “Prepare meu app para submissão ao ChatGPT.” → Inspecionar ferramentas e efeitos reais; gerar o contrato JSON quando houver evidência suficiente e separar achados do arquivo de importação.

Para procedência, correspondência dos módulos e mudanças desta conversão, consultar [origem.md](references/origem.md). Conservar a licença [Apache 2.0](LICENSE) ao redistribuir.
