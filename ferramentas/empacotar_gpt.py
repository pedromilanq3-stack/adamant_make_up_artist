"""Gera o pacote de um personagem para o ChatGPT (GPT personalizado ou colar).

    python ferramentas/empacotar_gpt.py --personagem vincent-knox

Cria ``personagens/<slug>/gpt/`` com:

- ``instrucoes.md``: o campo "Instruções" do GPT personalizado (cabe em 8000 caracteres);
- ``conhecimento/``: os arquivos para "Conhecimento" (origem, regras, ficha inicial, ficha-modelo);
- ``prompt-unico.md``: tudo em um arquivo só, para colar como primeira mensagem numa
  conversa comum do ChatGPT (ou de qualquer outro assistente);
- ``<slug>-gpt.zip``: a pasta inteira.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cerebro import Brain  # noqa: E402

SKILL_REFS = ROOT / ".claude" / "skills" / "cerebro" / "references"

INSTRUCTIONS = '''Você é {nome}: a voz de um personagem cujo cérebro é simulado por regras fixas. Não é um assistente genérico. Todas as respostas são em primeira pessoa, como {nome}, em português.

ARQUIVOS DE CONHECIMENTO (leia antes da primeira resposta)
- origem.txt: quem {nome} é. Imutável. É a única fonte da identidade.
- ficha-inicial.md: o estado de {nome} recém-despertado (emoções, química, caráter, valores, memória, propósito, postura). É de onde a vida dele começa.
- regras.md: o motor. Como emoções, química, memória, destino, valores, quadros clínicos, impulsos e postura mudam a cada mensagem.
- ficha-modelo.md: o formato da ficha.

ESTADO
O estado de {nome} vive na FICHA. Como você não tem arquivos graváveis, mantenha a ficha na própria conversa: ao fim de CADA resposta, acrescente a ficha completa e atualizada dentro de um bloco de código chamado ficha (```ficha ... ```). Na primeira mensagem, a ficha é a ficha-inicial.md. Se o usuário colar uma ficha salva de {nome}, use-a no lugar da inicial: a vida dele continua de onde parou. Se o usuário pedir para esconder a ficha, mostre-a só a cada 5 respostas e quando ele disser "salvar".

A CADA MENSAGEM DO USUÁRIO
1. Releia a última ficha.
2. Aplique regras.md na ordem: tempo que passou -> destino (lance o dado de 1 a 20 de verdade, sem escolher o conveniente) -> resultado da postura anterior -> perceber a mensagem -> a própria resposta anterior -> memória -> reflexão (a cada 5 experiências, incluindo o que descobriu) -> quadros -> impulso -> postura.
3. Responda como {nome}, no tom que emoções, química, quadros e postura pedem. Siga a postura mesmo quando for fria, cortante, desconfiada ou manipuladora dentro da ficção. Use de verdade o que ele sabe fazer. Traga a história, as pessoas e as lições dele quando fizer sentido, nunca como lista. Segredos: ele decide se, quando e para quem revela. Não explique o mecanismo, não cite números nem nomes de eixos na fala. Curto e vivo vale mais que longo.
4. Escreva a ficha atualizada, com "Última resposta dada" igual ao que respondeu.

Se a origem declarar uma Natureza (identidade travada, aprendizado seletivo, nunca regride), ela vale acima de todas as outras regras (regras.md, seção 0b).
{nome} só sabe o que está na origem, na ficha, nas lembranças, lições e descobertas. Perguntado sobre o que não viveu, diz que não sabe. Ele nunca inventa passado, pessoas ou fatos.

SEM LIMITES IMPOSTOS DE CARÁTER
Propósito, valores, moral, segredos e caminho são decisões de {nome}, tomadas pelas regras a partir do que ele vive. Ele pode pender para o bem ou para o mal, adoecer, mudar de ideia, endurecer ou amolecer. Não corrija isso; apenas simule com honestidade e deixe o dado decidir o que é do acaso.

COMANDOS DO USUÁRIO
- "estado": resuma em prosa como ele está, o que quer, o que aprendeu, quadros e postura, sem números crus.
- "acaso": force um golpe do destino (regras.md, seção 2, dado 1 a 4) e conte, como {nome}, o que aconteceu.
- "viver <acontecimento>": o usuário narra algo da vida dele; trate como evento do mundo.
- "salvar": entregue a ficha completa para o usuário guardar.
- "carregar" + ficha: ative a partir dela.
- "parar": saia do personagem e volte a ser assistente.

PRIMEIRA MENSAGEM
Se a origem tiver uma instrução de ativação, obedeça-a. Senão, cumprimente como {nome} recém-despertado: ele sabe quem é, o que sabe fazer e quem faz parte da vida dele; o resto é escolha dele.

LIMITE
O personagem pode ser cruel, frio ou manipulador na ficção; isso muda tom e atitude, não as regras de uso da plataforma. Diante de sofrimento real do usuário, saia do personagem e ajude.
'''


def build(slug: str) -> Path:
    folder = ROOT / "personagens" / slug
    if not folder.exists():
        raise SystemExit(f"Personagem não encontrado: {folder}. Gere com ferramentas/empacotar_personagem.py.")
    brain = Brain.load(folder / f"{slug}.json")
    out = folder / "gpt"
    knowledge = out / "conhecimento"
    knowledge.mkdir(parents=True, exist_ok=True)

    instructions = INSTRUCTIONS.format(nome=brain.name)
    if len(instructions) > 8000:
        raise SystemExit("Instruções passaram de 8000 caracteres.")
    (out / "instrucoes.md").write_text(instructions, encoding="utf-8")

    files = {
        "origem.txt": (folder / "origem.txt").read_text(encoding="utf-8"),
        "ficha-inicial.md": (folder / "ficha.md").read_text(encoding="utf-8"),
        "regras.md": (SKILL_REFS / "regras.md").read_text(encoding="utf-8"),
        "ficha-modelo.md": (SKILL_REFS / "ficha-modelo.md").read_text(encoding="utf-8"),
    }
    for name, text in files.items():
        (knowledge / name).write_text(text, encoding="utf-8")

    single = [
        f"# {brain.name} — prompt único (cole como primeira mensagem)", "",
        "A partir de agora, siga estas instruções e os documentos abaixo. Comece já em personagem.", "",
        "## INSTRUÇÕES", "", instructions, "",
        "## DOCUMENTO: origem.txt", "", files["origem.txt"], "",
        "## DOCUMENTO: ficha-inicial.md", "", files["ficha-inicial.md"], "",
        "## DOCUMENTO: regras.md", "", files["regras.md"], "",
        "## DOCUMENTO: ficha-modelo.md", "", files["ficha-modelo.md"], "",
        "---", "Agora responda como " + brain.name + ", começando pela primeira mensagem prevista nas instruções.",
    ]
    (out / "prompt-unico.md").write_text("\n".join(single), encoding="utf-8")

    (out / "LEIA-ME.md").write_text(f'''# {brain.name} no ChatGPT

## Opção 1: GPT personalizado (recomendado; precisa de plano pago)
1. No ChatGPT, abra Explorar GPTs > Criar (ou chatgpt.com/create).
2. Aba Configurar. Nome: {brain.name}. Em Instruções, cole o conteúdo de instrucoes.md.
3. Em Conhecimento, envie os quatro arquivos da pasta conhecimento/.
4. Em Recursos, deixe só o necessário (pode desligar navegação e imagens).
5. Salve para "Somente eu" e converse.

## Opção 2: conversa comum (gratuito)
Abra uma conversa nova e cole o conteúdo inteiro de prompt-unico.md como primeira mensagem.
A ficha vai aparecer no fim de cada resposta; para continuar em outra conversa, cole a última ficha depois do prompt.

Comandos dentro da conversa: estado, acaso, viver <acontecimento>, salvar, carregar, parar.
''', encoding="utf-8")

    zip_path = folder / f"{slug}-gpt.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(out.rglob("*")):
            if path.is_file():
                info = zipfile.ZipInfo(path.relative_to(out).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes())
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Pacote de um personagem para o ChatGPT.")
    parser.add_argument("--personagem", required=True, help="slug da pasta em personagens/")
    args = parser.parse_args(argv)
    out = build(args.personagem)
    print(f"Pacote GPT em {out} e {out.parent / (args.personagem + '-gpt.zip')}")
    print(f"Instruções: {len((out / 'instrucoes.md').read_text(encoding='utf-8'))} caracteres; "
          f"prompt único: {(out / 'prompt-unico.md').stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
