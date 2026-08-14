# Arquivo Local — pesquisa em exportações do Instagram

Aplicação local para localizar mensagens **já contidas** no ZIP oficial que o próprio titular obtém em **Instagram → Central de Contas → Suas informações e permissões → Baixar suas informações**. Aceita somente ZIP e interpreta os formatos JSON e HTML de mensagens.

> **Esta aplicação não “recupera” conteúdo apagado.** Ela não consulta o Instagram e não consegue obter conteúdo ausente da exportação oficial fornecida pelo titular.

## Executar

Requer Python 3.11 ou posterior e não possui dependências externas:

```bash
python -m instagram_archive.web
```

Abra `http://127.0.0.1:8765`. O servidor escuta apenas no dispositivo local.

## Escopo e privacidade

- Pesquisa por nome de usuário/nome exibido, intervalo de datas e palavras-chave.
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

## Instagram Graph API (Business Discovery)

Para coletar as informações **públicas disponibilizadas pela API** de uma conta
profissional, como `maysanchess`, configure um token válido e o ID numérico da sua
própria conta profissional conectada a uma Página do Facebook:

```bash
export INSTAGRAM_ACCESS_TOKEN='seu-token'
export INSTAGRAM_USER_ID='id-numerico-da-sua-conta'
python -m instagram_archive.graph_api maysanchess --output maysanchess.json
```

O coletor usa Business Discovery, pagina as mídias e salva perfil, biografia,
site, contagens públicas, URLs e metadados das publicações que a API autorizar.
O limite padrão é 500 mídias e pode ser alterado com `--max-media`. Para fixar
ou atualizar a versão da API, use `INSTAGRAM_GRAPH_API_VERSION` (por exemplo,
`v26.0`). O token é enviado no cabeçalho de autorização e nunca é salvo no JSON.

Essa integração não acessa mensagens diretas, e-mail, telefone, dados apagados,
informações privadas nem contas pessoais. A Meta exige as permissões e a revisão
de aplicativo aplicáveis; sem credenciais válidas não é possível executar a
coleta real. Respeite a autorização do titular e os termos da plataforma.
