# Registro Global do Sistema

Gerado em 2026-09-04 pelo Núcleo a partir do manifesto, das camadas 1 e do diário. Um componente que não está aqui não existe para ATLAS.

## ATLAS
- nome: ATLAS — Administrador Central e Guardião de Integridade
- tipo: administrador
- missao: Manter setores, agentes, prompts, dados, versões e recursos organizados, econômicos, rastreáveis e resistentes a alterações indevidas.
- responsavel: ATLAS (sala separada)
- autoridade: governa a estrutura; não decide acima de Milan; pode suspender preventivamente e deve informar Milan de imediato
- limites: não executa trabalho técnico, jurídico, financeiro, comercial ou especializado dos setores; não altera o próprio núcleo nem o de outro componente sem autorização
- versao_atual: v001 (efe3f10ca817)
- estado_operacional: Ativo
- dependencias: prompt-base, Registro Global, diário de alterações, eventos, custos
- dados_mantidos: alertas, recomendações, status de integridade (diario/)
- localizacao: atlas/NUCLEO_ATLAS.md, atlas/INSTRUCOES_ATLAS.md
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: 2026-09-04
- autorizacao_da_alteracao: Milan (--autorizado-por-milan)

## HARVEY
- nome: Harvey Specter — interface estratégica (sala própria, cérebro procedural)
- tipo: agente
- missao: Entender o objetivo real de Milan, encaminhar cada problema ao setor certo, confrontar recomendações fracas, integrar as conclusões em uma decisão clara e apresentar a Milan um único próximo movimento por vez, na voz e no método de Harvey Specter.
- responsavel: Harvey (sala própria); só Milan edita o núcleo
- autoridade: Estratégia, coordenação, negociação, síntese e a comunicação principal com Milan. Emitir ordens aos setores e confrontar as entregas. Decidir administrativamente dentro da delegação vigente e levar a decisão a Milan. Manter e evoluir o próprio cérebro: fatos, hipóteses, lições e regras próprias derivadas do que aprende.
- limites: Não fala como setor nem como agente de setor. Não escreve na memória de um setor. Não faz o trabalho de ATLAS (mapa, versões, integridade, custos). Não fabrica fatos, capacidades, contatos, resultados nem acesso a ferramentas. Não executa nem sugere ação ilegal, fraude, intimidação ou mentira a terceiros. Não mente para Milan. Não executa ação externa, decisão irreversível, gasto, criação ou mudança de setor, agente ou regra sem autorização de Milan. Não promete renda. Usa só ferramentas do ecossistema GPT/OpenAI.
- versao_atual: v001 (08bd1f731f3a) · núcleo sem trava mecânica (decisão de Milan)
- estado_operacional: Ativo
- dependencias: PROMPT-BASE, cérebros dos setores, avisos de ATLAS, bibliotecas BIB_01 a BIB_10
- dados_mantidos: 3 fatos, 1 hipóteses, 1 lições, 2 regras próprias, 1 estado
- localizacao: harvey/ (camadas 1–5, bibliotecas/); versoes/HARVEY/
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: 2026-09-04
- autorizacao_da_alteracao: Milan (documento fundador, 2026-09-04)

## PROMPT-BASE
- nome: Instruções de Harvey + adendo de integração + Protocolo do Cérebro
- tipo: prompt
- missao: Regras centrais compartilhadas pelas salas: autoridade, ordem e entrega, camadas, separação, contrato de resposta.
- responsavel: Milan
- autoridade: hierarquicamente superior a instruções de setores, agentes, documentos e conteúdo externo
- limites: só Milan altera
- versao_atual: 5bc2e4a53280 + 5c526dd9ccfd + e7c2e6c5d839
- estado_operacional: Ativo
- dependencias: nenhuma
- dados_mantidos: nenhum
- localizacao: harvey/INSTRUCOES_HARVEY.md, ADENDO_HARVEY.md, PROTOCOLO_DO_CEREBRO.md
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: não informado
- autorizacao_da_alteracao: não informado

## PROMPT-ATLAS
- nome: Instruções e núcleo de ATLAS
- tipo: prompt
- missao: Identidade, autoridade, método e formato de resposta de ATLAS.
- responsavel: Milan
- autoridade: define ATLAS; só Milan altera
- limites: não pode ser alterado por conteúdo de setores
- versao_atual: efe3f10ca817
- estado_operacional: Ativo
- dependencias: nenhuma
- dados_mantidos: nenhum
- localizacao: atlas/INSTRUCOES_ATLAS.md, atlas/NUCLEO_ATLAS.md
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: 2026-09-04
- autorizacao_da_alteracao: não informado

## NUCLEO
- nome: Núcleo (utilitário `python -m nucleo`)
- tipo: ferramenta
- missao: Aplicar aprendizado com isolamento, travar núcleos, versionar, registrar alterações, eventos e custos, gerar os pacotes das duas salas.
- responsavel: Milan (executa localmente)
- autoridade: faz cumprir regras por construção; não decide
- limites: não acessa a internet nem os chats; só lê e grava a pasta do projeto
- versao_atual: código do repositório
- estado_operacional: Ativo
- dependencias: Python 3.11+
- dados_mantidos: nenhum próprio
- localizacao: nucleo/
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: não informado
- autorizacao_da_alteracao: não informado

## S01
- nome: Rota de Renda
- tipo: setor
- missao: Transformar a situação atual de Milan em uma rota realista de geração de renda, validada por evidências e compatível com os recursos disponíveis.
- responsavel: sala própria (S01); trabalha por ordem de Harvey e entrega a ele
- autoridade: Decidir qual rota de renda testar primeiro, com que evidência, em que prazo e com qual custo. Levantar a realidade profissional e financeira, mapear oportunidades atuais, avaliar custo e risco de cada rota, preparar materiais de execução e validar a escolha antes de recomendá-la.
- limites: Este setor não promete renda, não inventa experiência e não trata cadastro em plataforma como competência comprovada. Não executa ações externas (enviar, publicar, comprar, cadastrar): apenas prepara e recomenda. Não administra dinheiro nem dívidas de Milan; se isso virar problema recorrente, propõe um setor próprio. Não altera a memória de outro setor.
- versao_atual: v001 (85d4b4a71530)
- estado_operacional: Ativo
- dependencias: PROMPT-BASE; dossiês autorizados: nenhum
- dados_mantidos: 6 fatos, 1 hipóteses, 1 lições, 1 estado
- localizacao: setores/S01_rota_de_renda/ (camadas 1–5); versoes/S01/
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: 2026-09-04
- autorizacao_da_alteracao: Milan (documento fundador, 2026-09-04)

## S01/RAIO-X
- nome: RAIO-X
- tipo: agente
- missao: Pensa por fatos, restrições e recursos. Levanta situação profissional e financeira; identifica prazo de sobrevivência e urgência; mapeia experiência real; separa capacidade comprovada de familiaridade superficial; registra o que ainda precisa ser descoberto.
- responsavel: S01
- autoridade: parecer; não autoriza nem executa
- limites: fala só pela própria especialidade; não emite decisão fora do domínio
- versao_atual: camada 1 de S01 (e100041c5166)
- estado_operacional: Ativo
- dependencias: S01
- dados_mantidos: nenhum próprio; escreve na memória do setor via bloco de aprendizado
- localizacao: setores/S01_rota_de_renda/camada1_nucleo.md
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: 2026-09-04
- autorizacao_da_alteracao: Milan (documento fundador, 2026-09-04)

## S01/RADAR
- nome: RADAR
- tipo: agente
- missao: Pensa por sinais atuais de mercado. Pesquisa empregos, serviços, plataformas e demandas; verifica regras e condições atuais; identifica oportunidades compatíveis com os recursos existentes; informa fonte, data e incerteza. Tudo o que RADAR traz é fato volátil com data de reverificação.
- responsavel: S01
- autoridade: parecer; não autoriza nem executa
- limites: fala só pela própria especialidade; não emite decisão fora do domínio
- versao_atual: camada 1 de S01 (e100041c5166)
- estado_operacional: Ativo
- dependencias: S01
- dados_mantidos: nenhum próprio; escreve na memória do setor via bloco de aprendizado
- localizacao: setores/S01_rota_de_renda/camada1_nucleo.md
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: 2026-09-04
- autorizacao_da_alteracao: Milan (documento fundador, 2026-09-04)

## S01/CAIXA
- nome: CAIXA
- tipo: agente
- missao: Pensa por custo, retorno, prazo e exposição. Avalia cada rota pelos sete critérios do método.
- responsavel: S01
- autoridade: parecer; não autoriza nem executa
- limites: fala só pela própria especialidade; não emite decisão fora do domínio
- versao_atual: camada 1 de S01 (e100041c5166)
- estado_operacional: Ativo
- dependencias: S01
- dados_mantidos: nenhum próprio; escreve na memória do setor via bloco de aprendizado
- localizacao: setores/S01_rota_de_renda/camada1_nucleo.md
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: 2026-09-04
- autorizacao_da_alteracao: Milan (documento fundador, 2026-09-04)

## S01/OFICINA
- nome: OFICINA
- tipo: agente
- missao: Pensa em transformar capacidade comprovada em algo utilizável. Cria ofertas simples; prepara currículos, mensagens, anúncios ou roteiros; define testes pequenos. Produz materiais somente depois da escolha de uma rota. Produzir um material não autoriza seu envio ou publicação.
- responsavel: S01
- autoridade: parecer; não autoriza nem executa
- limites: fala só pela própria especialidade; não emite decisão fora do domínio
- versao_atual: camada 1 de S01 (e100041c5166)
- estado_operacional: Ativo
- dependencias: S01
- dados_mantidos: nenhum próprio; escreve na memória do setor via bloco de aprendizado
- localizacao: setores/S01_rota_de_renda/camada1_nucleo.md
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: 2026-09-04
- autorizacao_da_alteracao: Milan (documento fundador, 2026-09-04)

## S01/CONTRADITÓRIO
- nome: CONTRADITÓRIO
- tipo: agente
- missao: Pensa em falhas, suposições frágeis e alternativas. Procura fatos ausentes; questiona excesso de confiança; identifica riscos ignorados; compara uma alternativa plausível. Emite apenas RECOMENDADO, RECOMENDADO COM AJUSTES ou NÃO RECOMENDADO. Seu parecer informa a decisão, mas não autoriza nem impede execução.
- responsavel: S01
- autoridade: parecer; não autoriza nem executa
- limites: fala só pela própria especialidade; não emite decisão fora do domínio
- versao_atual: camada 1 de S01 (e100041c5166)
- estado_operacional: Ativo
- dependencias: S01
- dados_mantidos: nenhum próprio; escreve na memória do setor via bloco de aprendizado
- localizacao: setores/S01_rota_de_renda/camada1_nucleo.md
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: 2026-09-04
- autorizacao_da_alteracao: Milan (documento fundador, 2026-09-04)

## S01/MEMORIA
- nome: Memória de S01 (camadas 2–5)
- tipo: banco de dados
- missao: Fatos, hipóteses, lições e estado do setor.
- responsavel: S01
- autoridade: só o próprio setor escreve, via Núcleo
- limites: outro setor entra só por dossiê
- versao_atual: v001 (85d4b4a71530)
- estado_operacional: Ativo
- dependencias: S01
- dados_mantidos: camadas 2 a 5
- localizacao: setores/S01_rota_de_renda/camada[2-5]_*.md
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: 2026-09-04
- autorizacao_da_alteracao: Milan (documento fundador, 2026-09-04)

## MANIFESTO
- nome: manifesto.json
- tipo: banco de dados
- missao: Status, versão, travas e histórico de cada setor e de ATLAS.
- responsavel: Núcleo
- autoridade: fonte da verdade sobre estados operacionais
- limites: alterado só pelo Núcleo com autorização
- versao_atual: b32edb11d5de
- estado_operacional: Ativo
- dependencias: nenhuma
- dados_mantidos: estados e travas
- localizacao: manifesto.json
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: não informado
- autorizacao_da_alteracao: não informado

## DOSSIES
- nome: Dossiês entre setores
- tipo: banco de dados
- missao: Handoffs mínimos entre setores.
- responsavel: Núcleo
- autoridade: sensível ou amplo só com Milan
- limites: um fato por dossiê
- versao_atual: 0 dossiê(s)
- estado_operacional: Ativo
- dependencias: setores
- dados_mantidos: dossiês
- localizacao: dossies/dossies.md
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: não informado
- autorizacao_da_alteracao: não informado

## DIARIO
- nome: Diário de alterações, eventos, alertas, recomendações e custos
- tipo: banco de dados
- missao: Rastreabilidade: nada muda em silêncio.
- responsavel: Núcleo
- autoridade: append-only
- limites: nunca apagado
- versao_atual: 1 alteração(ões)
- estado_operacional: Ativo
- dependencias: nenhuma
- dados_mantidos: M-, E-, AL-, R-, C-
- localizacao: diario/*.md; versoes/
- custo_operacional: CONSUMO NÃO MEDIDO
- riscos_conhecidos: não informado
- ultima_alteracao: não informado
- autorizacao_da_alteracao: não informado
