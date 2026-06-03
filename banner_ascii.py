"""banner_ascii.py — gerador de banner ASCII da Mission Control AI.

Script auxiliar standalone para experimentar fontes e customizar o banner.

Uso:
    python banner_ascii.py                 # banner padrão (ansi_shadow, ciano)
    python banner_ascii.py --fonts         # lista as 570+ fontes do PyFiglet
    python banner_ascii.py --font slant --text "Mission Control AI"
    python banner_ascii.py --demo          # mostra 8 fontes lado a lado
"""

import sys

import pyfiglet
from rich.console import Console
from rich.align import Align
from rich.text import Text

console = Console()

# Paleta da CLI (estilo Claude Code)
ROXO = "bold #A855F7"
CIANO = "bold #06B6D4"
CINZA = "italic #8484A0"


def banner_padrao(texto_topo="Global Solution", texto_base="Mission Control AI",
                  fonte="ansi_shadow"):
    """Gera as duas linhas do banner em ASCII art e imprime centralizado."""
    linha1 = pyfiglet.figlet_format(texto_topo, font=fonte)
    linha2 = pyfiglet.figlet_format(texto_base, font=fonte)

    # Pinta em gradiente roxo -> ciano e centraliza
    console.print(Align.center(Text(linha1, style=ROXO)))
    console.print(Align.center(Text(linha2, style=CIANO)))
    console.print(Align.center(
        Text(" ──  2026.1 · Prompt Engineering and AI · FIAP ── ", style=CINZA)
    ))


def listar_fontes():
    """Lista todas as fontes disponíveis no PyFiglet."""
    fontes = sorted(pyfiglet.FigletFont.getFonts())
    console.print(f"[bold]{len(fontes)} fontes disponíveis no PyFiglet:[/bold]\n")
    console.print(", ".join(fontes))


def testar_fonte(fonte, texto):
    """Renderiza um texto com uma fonte específica."""
    try:
        arte = pyfiglet.figlet_format(texto, font=fonte)
        console.print(Text(arte, style=CIANO))
    except pyfiglet.FontNotFound:
        console.print(f"[red]Fonte '{fonte}' não encontrada.[/red] "
                      f"Use --fonts para listar as disponíveis.")


def demo():
    """Demonstra 8 fontes diferentes com a frase 'Mission Control AI'."""
    fontes_demo = ["ansi_shadow", "slant", "standard", "big",
                   "banner3", "doom", "small", "block"]
    for fonte in fontes_demo:
        console.rule(f"[bold #06B6D4]{fonte}[/bold #06B6D4]")
        testar_fonte(fonte, "Mission Control AI")


def main(argv):
    """Roteia os argumentos de linha de comando."""
    if "--fonts" in argv:
        listar_fontes()
        return
    if "--demo" in argv:
        demo()
        return

    # --font <nome> e --text "<texto>"
    fonte = "ansi_shadow"
    texto = None
    if "--font" in argv:
        fonte = argv[argv.index("--font") + 1]
    if "--text" in argv:
        texto = argv[argv.index("--text") + 1]

    if texto is not None:
        testar_fonte(fonte, texto)
    else:
        banner_padrao(fonte=fonte)


if __name__ == "__main__":
    main(sys.argv[1:])
