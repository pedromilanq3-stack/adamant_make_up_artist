# Arquivo Local — pesquisa em exportações do Instagram

> **Utilitário adicional:** este repositório também contém um userscript independente
> para Tinder Web, com Dry Run, controles de segurança e decisões sem análise de
> imagens. Consulte [`docs/TINDER_BOT.md`](docs/TINDER_BOT.md) e copie
> [`tinder-bot.user.js`](tinder-bot.user.js) para o Tampermonkey.
>
> **Utilitário adicional 2:** também há um userscript de mensagens assistidas para
> Tinder Web — seleção manual de conversas, composição de mensagem, fila local e
> confirmação manual obrigatória antes de cada envio, com parada imediata diante de
> CAPTCHA/bloqueio. Consulte [`docs/TINDER_MESSAGES.md`](docs/TINDER_MESSAGES.md) e
> copie [`tinder-messages.user.js`](tinder-messages.user.js) para o Tampermonkey.
>
> **Utilitário adicional 3:** o mesmo assistente de mensagens existe também para o
> Sexlog (seletores ainda não confirmados nesse site — valide com Dry Run antes de
> qualquer envio real). Consulte [`docs/SEXLOG_MESSAGES.md`](docs/SEXLOG_MESSAGES.md)
> e copie [`sexlog-messages.user.js`](sexlog-messages.user.js) para o Tampermonkey.
>
> **Utilitário adicional 5:** o pacote [`cerebro/`](docs/CEREBRO.md) cria um
> personagem com sentimentos, memória, evolução e caráter que pode pender para o bem
> ou para o mal conforme o que vive e escolhe, sujeito a adversidades, ao acaso e à
> própria imprevisibilidade, com crescimento procedural (aprende com o resultado das
> próprias escolhas, forma valores, elege um propósito) e um corpo com sinapses e
> hormônios, do qual podem emergir depressão, ansiedade ou bipolaridade. Ele nasce de
> uma descrição de si,
> sempre presente na conversa, e é implantado como *system prompt* em qualquer chat.
> Sem instalar nada: a skill em [`.claude/skills/cerebro/`](.claude/skills/cerebro/SKILL.md)
> faz o próprio modelo simular o cérebro (mande `/cerebro criar Nome: descrição`); para o
> Claude.ai, envie [`cerebro-skill.zip`](cerebro-skill.zip) como skill personalizada.
> Instalação fácil: baixe [`cerebro.pyz`](cerebro.pyz) e dê clique duplo em
> [`Cerebro.bat`](Cerebro.bat) (Windows) ou [`Cerebro.command`](Cerebro.command) (Mac e
> Linux); no Android, baixe só [`cerebro_android.py`](cerebro_android.py) e execute no
> Pydroid 3 (passo a passo em [`docs/CEREBRO.md`](docs/CEREBRO.md)). O chat abre no
> navegador com o cérebro vivo ao lado. `python cerebro.pyz registrar` acompanha
> conversas feitas em outro app.
>
> **Utilitário adicional 4:** o [`Tinder Boost Helper`](docs/TINDER_BOOST_HELPER.md)
> detecta e ativa somente Boosts já disponibilizados pelo fluxo oficial, bloqueia
> telas de compra e permite apagar apenas o histórico local do script. Copie
> [`tinder-boost-helper.user.js`](tinder-boost-helper.user.js) para o Tampermonkey.

Aplicação local para localizar mensagens **já contidas** no ZIP oficial que o próprio titular obtém em **Instagram → Central de Contas → Suas informações e permissões → Baixar suas informações**. Aceita somente ZIP e interpreta os formatos JSON e HTML de mensagens.

> **Esta aplicação não “recupera” conteúdo apagado.** Ela não consulta o Instagram e não consegue obter conteúdo ausente da exportação oficial fornecida pelo titular.

## O que ela consegue ver no celular

A aplicação **não acessa nem examina o aparelho automaticamente**. Um navegador não
concede a ela acesso geral a aplicativos, conversas, fotos, bancos de dados ou arquivos
apagados. Ela vê somente o ZIP do Instagram que o titular selecionar manualmente.

Para conferir outros dados do próprio aparelho, use primeiro os recursos oficiais:

- **Android:** `Configurações → Armazenamento`, o aplicativo `Files/Meus Arquivos` e
  `Configurações → Apps` para revisar arquivos, aplicativos e permissões.
- **iPhone:** `Ajustes → Geral → Armazenamento do iPhone`, os aplicativos `Arquivos` e
  `Fotos → Apagados`, e `Ajustes → Privacidade e Segurança` para revisar permissões.

Não forneça senha, PIN, cookies, tokens ou códigos 2FA a programas de “recuperação”.
Caso seja necessária uma perícia completa, preserve o aparelho e procure um profissional
autorizado; este projeto não importa backups completos nem contorna a segurança do celular.

## Executar

Requer Python 3.11 ou posterior e não possui dependências externas:

```bash
python -m instagram_archive.web
```

Abra `http://127.0.0.1:8765`. O servidor escuta apenas no dispositivo local.

### Primeiro uso, passo a passo

1. No Instagram, abra **Central de Contas → Suas informações e permissões →
   Baixar suas informações**.
2. Solicite as mensagens no formato **JSON** e espere a Meta concluir a preparação.
3. Baixe o arquivo `.zip` e **não o descompacte**.
4. Em um computador com este projeto, execute `python -m instagram_archive.web`
   (`py -m instagram_archive.web` também pode ser usado no Windows).
5. Abra `http://127.0.0.1:8765`, selecione o ZIP e clique em **Importar com
   segurança**.
6. Informe o `@` procurado no campo de pesquisa e clique em **Pesquisar
   localmente**.

O endereço `127.0.0.1` só abre no mesmo aparelho em que o programa está sendo
executado. Se o ZIP foi baixado no celular, transfira-o para o computador antes do
passo 4. Não é possível pesquisar enquanto o download ainda estiver incompleto.

### Executar no Android com Pydroid 3

O texto `python -m instagram_archive.web` é um **comando de terminal**, não código
Python. Se ele for escrito na tela do editor do Pydroid, aparecerá `SyntaxError`.

No Pydroid 3, faça assim:

1. Baixe este projeto completo e descompacte **o projeto** em uma pasta. Não
   descompacte o ZIP da exportação do Instagram.
2. No Pydroid, abra o arquivo `iniciar.py` que está na pasta principal do projeto.
3. Toque no botão de executar. Não escreva `python -m ...` dentro do arquivo.
4. Mantenha o Pydroid aberto e, no navegador do mesmo celular, acesse
   `http://127.0.0.1:8765`.
5. Selecione o ZIP original da exportação do Instagram.

Alternativamente, quem estiver usando o **Terminal** do Pydroid pode entrar na pasta
do projeto e executar `python iniciar.py`. A mensagem `Abra
http://127.0.0.1:8765` confirma que o servidor iniciou.

## Escopo e privacidade

- Pesquisa investigativa por @ atual ou antigo em título, participantes, remetente,
  texto, caminhos de anexos e nome do arquivo de origem. A comparação tolera `@`,
  acentos, pontos, sublinhados e diferenças entre maiúsculas e minúsculas.
- Cada resultado informa o campo da correspondência e o arquivo de origem, além de
  aceitar intervalo de datas e palavras-chave.
- Exibe, quando solicitado, até cinco mensagens anteriores e posteriores a cada ocorrência para preservar o contexto da conversa.
- Não pesquisa CPF, telefone, endereço nem bancos de dados externos.
- Não solicita nem persiste senha, cookies, token, código 2FA ou qualquer credencial.
- Não acessa contas e não ajuda a contornar controles da Meta ou descobrir dados privados de terceiros.
- Não há integração com GPT: toda análise é local. A interface anonimiza automaticamente CPF, telefone, e-mail e endereço nos resultados (opção controlada pelo titular).
- Uma integração futura com serviço externo deverá transmitir apenas trechos escolhidos pelo titular e mostrar uma confirmação específica antes de cada envio.
- A extração usa diretório temporário, apagado ao encerrar normalmente. O botão **Eliminar índice local e temporários** permite a remoção explícita durante a execução.

## Segurança do importador

Antes de extrair, a aplicação bloqueia caminhos absolutos, `..`, caminhos Windows e links simbólicos (Zip Slip); executáveis e extensões inesperadas; arquivos individuais acima de 100 MB; ZIPs acima de 250 MB; conteúdo extraído acima de 750 MB; mais de 20.000 entradas; e taxas de compressão suspeitas. Anexos são referenciados somente quando existem dentro da própria exportação.

Esses limites são medidas de redução de risco, não uma garantia para abrir arquivos de origem desconhecida. Use exclusivamente sua própria exportação oficial.

## Testes

```bash
python -m unittest discover -s tests -v
```

Todas as fixtures são geradas sinteticamente durante os testes. Elas cobrem JSON, HTML, Unicode, anexos presentes e ausentes, anonimização, extensões inesperadas e ZIPs maliciosos; nenhuma mensagem ou documento real é versionado.
