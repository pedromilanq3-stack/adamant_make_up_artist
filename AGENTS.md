# Guia para agentes (Codex, Claude Code e outros)

Este repositório tem dois projetos independentes. O mais recente é o **cérebro**: um
personagem simulado com emoções, neuroquímica, memória, valores em evolução, destino e
leis de natureza. Tudo dele está na branch `claude/brain-evolution-feelings-t1hps7`
(faça `git fetch origin claude/brain-evolution-feelings-t1hps7 && git checkout claude/brain-evolution-feelings-t1hps7`
se não estiver nela).

## Onde estão os arquivos do cérebro

| O quê | Onde |
|---|---|
| Motor em Python (sem dependências, 3.11+) | `cerebro/` — `brain.py` (núcleo), `emotions.py`, `neurochemistry.py`, `memory.py`, `perception.py`, `personality.py`, `growth.py` (valores, propósito, encruzilhadas), `fate.py` (adversidades, acaso, impulsos), `origin.py` (ficha de origem e leis de natureza), `ficha.py` (exporta a ficha da skill), `session.py` (implante na conversa e adaptadores), `web.py` (chat local), `__main__.py` (CLI) |
| Documentação completa | `docs/CEREBRO.md` |
| Testes | `tests/test_cerebro.py` — rode `python -m unittest discover -s tests` (tudo deve passar) |
| Skill genérica (o modelo simula o cérebro sem código) | `.claude/skills/cerebro/` e cópia em `.agents/skills/cerebro/` — `SKILL.md`, `references/regras.md`, `references/ficha-modelo.md` |
| Personagens prontos | `personagens/<slug>/` — `origem.txt` (história), `<slug>.json` (cérebro do motor despertado), `ficha.md` (estado no formato da skill), `<slug>-skill.zip` (skill do personagem para Claude.ai), `gpt/` (instruções, conhecimento e prompt único para ChatGPT), `<slug>-gpt.zip`, `<slug>-tudo.zip` (tudo junto) |
| Personagens existentes | `personagens/vincent-knox/` (COO, Vincent Knox) e `personagens/harvey-specter/` (Harvey Specter, com leis de natureza: identidade travada, aprendizado seletivo, nunca regride) |
| Skills dos personagens instaladas no projeto | `.claude/skills/<slug>/` e `.agents/skills/<slug>/` — invocadas com `/<slug>` |
| Programa em arquivo único | `cerebro.pyz` (`python cerebro.pyz` abre o chat local), `cerebro_android.py` (Pydroid 3), `Cerebro.bat`, `Cerebro.command`, `instalar_termux.sh` |
| Tudo junto | `personagens-tudo.zip` (todos os personagens + programa + skill genérica) |

## Ferramentas (pasta `ferramentas/`)

- `empacotar_personagem.py --nome "Nome" --origem historia.txt [--genero f] [--instalar]`: cria `personagens/<slug>/` a partir de uma história; `--instalar` copia a skill para `.claude/skills/` e `.agents/skills/`.
- `empacotar_gpt.py --personagem <slug>`: gera o pacote para ChatGPT.
- `empacotar_tudo.py --personagem <slug>` ou `--todos`: zips com tudo.
- `empacotar_cerebro.py`: regenera `cerebro.pyz` e `cerebro_android.py` (obrigatório após mudar `cerebro/`; há um teste que confere).
- `empacotar_skill.py`: regenera `cerebro-skill.zip` (obrigatório após mudar `.claude/skills/cerebro/`).

## Formato da ficha de origem

Texto com seções rotuladas, uma por linha: descrição livre no início, depois
`História:`, `Habilidades:` (nível entre parênteses: mestre, avançado, bom, básico,
iniciante), `Relações:`, `Medos:`, `Segredos:`, `Não sei:`, `Natureza:` (leis:
"identidade travada", "aprendizado seletivo", "nunca regride"). Itens separados por
`;` (vírgulas ficam dentro do item). Exemplo completo em `personagens/harvey-specter/origem.txt`.

## Regras de trabalho

- Depois de qualquer mudança em `cerebro/`, rode `python ferramentas/empacotar_cerebro.py` e os testes.
- Depois de mudar a skill genérica, rode `python ferramentas/empacotar_skill.py` e regenere os personagens com `empacotar_personagem.py` (os zips deles incluem `regras.md`).
- Não invente limites de caráter para os personagens: propósito, valores, moral e segredos são decisões deles, pelas regras.
- O outro projeto do repositório (`instagram_archive/`, userscripts `*.user.js`) é independente e está descrito no `README.md`.
