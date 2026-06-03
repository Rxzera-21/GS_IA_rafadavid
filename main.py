"""Mission Control AI — ponto de entrada do sistema.

Trilha: EnviroSat (Observação Ambiental).
Apenas instancia o motor (MissionEngine) e entrega o controle para a UI.
Toda a lógica de domínio fica em src/engine.py, src/telemetria.py e src/alertas.py.

Execução:
    python main.py
"""

from src.ui import run_cli
from src.engine import MissionEngine

if __name__ == "__main__":
    # O motor concentra telemetria + alertas + integração com a IA.
    engine = MissionEngine()
    # A UI cuida do banner, do loop de input e do despacho para engine.analyze().
    run_cli(engine)
