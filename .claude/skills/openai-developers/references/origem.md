# Origem e adaptação

Conversão independente preparada em 2026-09-05 a partir do arquivo fornecido pelo usuário `openai-developers-for-claude-main.zip`.

- Projeto identificado no arquivo: OpenAI Developers Plugin for Claude Code.
- Repositório indicado pelo README: https://github.com/openai/openai-developers-for-claude
- Comentário do ZIP original: `3c5c0debdec2695f657c5f1b99a32df6d23dd0ed`.
- SHA-256 do ZIP original: `03b06a619af013685f50d9d2b5287bec48d276e586985efe6543f35c761c906d`.
- Licença original preservada integralmente em [LICENSE](../LICENSE): Apache License 2.0.
- Esta conversão não é apresentada como uma edição oficial da OpenAI ou da Anthropic.

## Correspondência

Cada referência técnica corresponde ao arquivo `plugins/openai-developers/skills/<nome>/SKILL.md` dentro da pasta raiz do ZIP original:

| Módulo de origem | Arquivo desta skill |
| --- | --- |
| `openai-docs` | [openai-docs.md](openai-docs.md) |
| `openai-platform-api-key` | [openai-platform-api-key.md](openai-platform-api-key.md) |
| `openai-api-troubleshooting` | [openai-api-troubleshooting.md](openai-api-troubleshooting.md) |
| `agents-sdk` | [agents-sdk.md](agents-sdk.md) |
| `build-chatgpt-app` | [build-chatgpt-app.md](build-chatgpt-app.md) |
| `chatgpt-app-submission` | [chatgpt-app-submission.md](chatgpt-app-submission.md) |

## Alterações aplicadas

- Criado um único SKILL.md com nome e descrição, roteamento em português e referências internas.
- Convertidos os seis módulos em referências de carregamento seletivo, conservando o conteúdo técnico original quando compatível.
- Substituídas referências a skills externas por links relativos; removidos pressupostos de MCP automaticamente instalado e acesso automático ao computador do usuário.
- Reescrito o módulo de credenciais para distinguir presença, validade e autorização, preservar segredos e permitir trabalho offline sem chave. Isso resolve a contradição do gate original com openai-docs.
- Adaptados os módulos de agentes e apps para condicionar credenciais somente a chamadas reais e distinguir testes executados de testes pendentes.
- Esclarecida a diferença entre erro de transporte, modelo inexistente e falta de acesso; removida instrução que poderia ser interpretada como contornar restrições de rede.
- Conservados o exemplo JSON de submissão, suas categorias, o subtítulo de até 30 caracteres e os cinco testes positivos/três negativos. Acrescentada a obrigação de verificar o contrato atual e de não inventar descritores ou efeitos externos.
- Respeitada autorização já concedida para correções de código, preservando a necessidade de autorização para alterações que estejam fora do pedido.
- Omitidos os arquivos do marketplace, configuração automática de MCP e testes de estrutura do plugin, pois não são necessários para importar esta skill.

## Formato consultado

Estrutura de skills e importação verificadas na documentação da Anthropic durante esta conversão:

- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- https://support.claude.com/en/articles/12512198-how-to-create-custom-skills
- https://support.claude.com/en/articles/12512180-use-skills-in-claude

Esta verificação confirma o formato documentado; a importação na conta Claude do usuário e a execução de APIs não foram realizadas nesta conversão.
