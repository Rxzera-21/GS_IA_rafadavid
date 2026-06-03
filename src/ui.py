"""Interface CLI estilo Claude Code — usa Rich + prompt-toolkit.

A camada de apresentação está resolvida: exibe banner ASCII, gerencia o loop de
input e despacha cada pergunta para engine.analyze(). A lógica de domínio fica
no motor (src/engine.py). Comandos de base: /help /status /about /clear /exit.
"""

from datetime import datetime

import pyfiglet
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()
CIANO = "#06B6D4"

# Estilo do prompt editável. A PromptSession é criada de forma preguiçosa dentro
# de run_cli() — instanciá-la no import quebra em ambientes sem console real.
_ESTILO_PROMPT = Style.from_dict({"prompt": "#06B6D4 bold"})


def show_banner():
    """Exibe banner ASCII colorido no início."""
    banner = pyfiglet.figlet_format("Mission Control", font="ansi_shadow")
    console.print(Text(banner, style=f"bold {CIANO}"))
    console.print(Panel.fit(
        "Bem-vindo à interface da Mission Control AI.\n"
        "Sistema de monitoramento e análise por IA generativa · Trilha EnviroSat.\n"
        "Use /help para ver os comandos · /exit para sair.\n"
        "Modelo: gpt-oss:120b via Ollama Cloud",
        title="◆  MISSION CONTROL",
        subtitle="connected",
        border_style=CIANO,
    ))


def show_response(text):
    """Renderiza resposta da IA em painel com timestamp."""
    now = datetime.now().strftime("%H:%M")
    console.print(Panel(text, title="◆  Mission Control",
                        subtitle=now, border_style=CIANO))


def show_help():
    """Mostra uma tabela com os comandos disponíveis."""
    tabela = Table(title="Comandos disponíveis", border_style=CIANO,
                   title_style=f"bold {CIANO}")
    tabela.add_column("Comando", style="bold #A855F7", no_wrap=True)
    tabela.add_column("Descrição")
    tabela.add_row("/help", "Mostra esta lista de comandos")
    tabela.add_row("/status", "Snapshot da telemetria atual + alertas")
    tabela.add_row("/about", "Sobre o projeto, a trilha e a persona atendida")
    tabela.add_row("/clear", "Limpa a tela e redesenha o banner")
    tabela.add_row("/exit", "Encerra a Mission Control AI")
    tabela.add_row("<pergunta>", "Qualquer texto livre vai para a análise da IA")
    console.print(tabela)


def show_about(engine):
    """Mostra informações do projeto e o estado da integração com a IA."""
    chave_ok = "OK ✓" if engine.api_key_presente() else "FALTANDO ✗"
    texto = (
        "[bold]Mission Control AI — Trilha EnviroSat (Observação Ambiental)[/bold]\n\n"
        "Satélite simulado de observação ambiental (sensor térmico + óptico),\n"
        "inspirado no Amazônia-1 / Landsat. Monitora focos de calor, integridade\n"
        "do payload e enlace de descida, traduzindo cada anomalia em impacto\n"
        "para o combate ao desmatamento e a incêndios florestais.\n\n"
        "[bold]Persona atendida:[/bold] operador de centro de controle ambiental\n"
        "(INPE / órgão estadual) e coordenador de brigada de incêndio.\n\n"
        f"[bold]Modelo:[/bold] {engine.modelo} via Ollama Cloud\n"
        f"[bold]Chave da API (.env):[/bold] {chave_ok}\n"
        f"[bold]Engine:[/bold] {'OPERACIONAL ✓' if engine.is_ready() else 'pendente ✗'}"
    )
    console.print(Panel(texto, title="◆  Sobre", border_style="#A855F7"))


def run_cli(engine):
    """Loop principal da CLI."""
    session = PromptSession(style=_ESTILO_PROMPT)
    show_banner()

    if not engine.is_ready():
        console.print("  ⚠  Engine status: AGUARDANDO IMPLEMENTAÇÃO ✗\n",
                      style="yellow")
    else:
        console.print("  ✓  Engine status: OPERACIONAL\n", style="green")
        if not engine.api_key_presente():
            console.print("  ⚠  Chave OLLAMA_API_KEY ausente no .env — "
                          "configure antes de analisar.\n", style="yellow")

    while True:
        try:
            user_input = session.prompt("❯  ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue
        if user_input == "/exit":
            break
        if user_input == "/help":
            show_help()
            continue
        if user_input == "/about":
            show_about(engine)
            continue
        if user_input == "/status":
            with console.status("[cyan]Coletando telemetria...[/cyan]"):
                snapshot = engine.status_snapshot()
            show_response(snapshot)
            continue
        if user_input == "/clear":
            console.clear()
            show_banner()
            continue

        # Qualquer outra entrada vai para o motor de análise.
        with console.status("[cyan]Mission Control AI analisando telemetria...[/cyan]"):
            resposta = engine.analyze(user_input)
        show_response(resposta)

    console.print("\n[dim]Encerrando Mission Control AI. Até a próxima órbita. 🛰[/dim]")
