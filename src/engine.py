"""Motor de análise da Mission Control AI — Trilha EnviroSat.

Combina:
  (a) a função llm() — ponto ÚNICO de contato com a Ollama Cloud (gpt-oss:120b);
  (b) a classe MissionEngine — orquestra telemetria + alertas + IA.

Fluxo do analyze():
    telemetria.coletar()  ->  alertas.avaliar()  ->  monta prompt com dados reais
    injetados dinamicamente  ->  llm(prompt, system=system_prompt)  ->  resposta.
"""

import os
from collections import deque
from pathlib import Path

from dotenv import load_dotenv
from ollama import Client

from src import telemetria
from src import alertas

load_dotenv()

# Identificação da trilha escolhida pelo grupo.
TRILHA = "envirosat"  # "agrosat" | "envirosat" | "connectsat" | "mobilitysat"

# Cliente Ollama Cloud — mesma configuração dos Checkpoints 02 e 03.
client = Client(
    host="https://ollama.com",
    headers={"Authorization": "Bearer " + os.environ.get("OLLAMA_API_KEY", "")},
)


def llm(prompt, system=None, max_tokens=800, temperature=0.3):
    """Envia prompt ao gpt-oss:120b via Ollama Cloud e retorna o texto.

    PONTO ÚNICO DE INTEGRAÇÃO COM A IA — toda chamada ao modelo passa por aqui.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        return client.chat(
            model="gpt-oss:120b",
            messages=messages,
            options={"num_predict": max_tokens, "temperature": temperature},
            stream=False,
        )["message"]["content"].strip()
    except Exception as e:
        return f"⚠  Erro ao consultar IA: {e}"


def load_system_prompt():
    """Lê o system prompt do arquivo prompts/system_prompt.md."""
    path = Path("prompts/system_prompt.md")
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "Você é um assistente."  # fallback genérico


class MissionEngine:
    """Motor de análise da missão EnviroSat."""

    def __init__(self):
        self.trilha = TRILHA
        self.system_prompt = load_system_prompt()
        self.modelo = "gpt-oss:120b"
        # Memória de contexto: histórico dos últimos ciclos (consciência temporal).
        self.historico = deque(maxlen=5)

    # ------------------------------------------------------------------ status
    def is_ready(self):
        """A lógica de análise está implementada -> motor operacional."""
        return True

    def api_key_presente(self):
        """Indica se a chave da Ollama foi carregada do .env."""
        chave = os.environ.get("OLLAMA_API_KEY", "")
        return bool(chave) and chave != "cole_sua_chave_aqui_sem_aspas"

    def status_snapshot(self):
        """Retorna texto resumindo o estado atual da telemetria + alertas."""
        dados = telemetria.coletar()
        diagnostico = alertas.avaliar(dados)
        self._registrar_historico(dados, diagnostico)
        return self._formatar_snapshot(dados, diagnostico)

    def _formatar_snapshot(self, dados, diagnostico):
        """Formata uma leitura + diagnóstico em texto legível para o painel."""
        modo = "cenário fixado" if telemetria.cenario_ativo() else "dinâmico"
        linhas = [
            f"🛰  EnviroSat · Ciclo #{dados['ciclo']} · {dados['timestamp']} "
            f"· modo: {modo}",
            f"📍 Região observada: {dados['regiao_observada']}",
        ]
        if dados.get("cenario"):
            linhas.append(f"🎬 Cenário: {dados['cenario']} — "
                          f"{dados.get('descricao_cenario', '')}")
        linhas.append("")
        linhas.append("Telemetria atual:")
        for chave, (rotulo, unidade) in telemetria.ROTULOS.items():
            linhas.append(f"  • {rotulo}: {dados[chave]} {unidade}")

        linhas.append("")
        linhas.append(alertas.resumo_textual(diagnostico))
        return "\n".join(linhas)

    # ---------------------------------------------------------------- cenários
    def cenarios_disponiveis(self):
        """Lista os nomes de cenários de teste disponíveis."""
        return telemetria.listar_cenarios()

    def carregar_cenario(self, nome):
        """Fixa um cenário de teste e retorna o snapshot resultante.

        Após fixado, todas as análises/status usam esses valores até limpar.
        Retorna None se o cenário não existir.
        """
        dados = telemetria.fixar_cenario(nome)
        if dados is None:
            return None
        diagnostico = alertas.avaliar(dados)
        self._registrar_historico(dados, diagnostico)
        return self._formatar_snapshot(dados, diagnostico)

    def limpar_cenario(self):
        """Volta ao modo dinâmico (telemetria por random walk)."""
        telemetria.limpar_cenario()

    # ----------------------------------------------------------------- análise
    def analyze(self, pergunta_usuario):
        """Analisa a pergunta com base na telemetria + alertas + IA generativa."""
        if not self.api_key_presente():
            return (
                "⚠  Chave da Ollama Cloud não configurada.\n\n"
                "Crie o arquivo .env na raiz com:\n"
                "    OLLAMA_API_KEY=sua_chave_aqui\n\n"
                "Gere a chave gratuitamente em https://ollama.com e rode novamente."
            )

        # 1. Coleta os dados simulados da telemetria (um ciclo).
        dados = telemetria.coletar()
        # 2. Avalia alertas e dispara respostas automáticas (lógica em Python).
        diagnostico = alertas.avaliar(dados)
        # 3. Guarda no histórico (memória de contexto).
        self._registrar_historico(dados, diagnostico)
        # 4. Monta o prompt com os dados reais injetados dinamicamente.
        prompt = self._montar_prompt(pergunta_usuario, dados, diagnostico)
        # 5. Chama a IA passando o system prompt da missão.
        return llm(prompt, system=self.system_prompt)

    # ----------------------------------------------------------------- helpers
    def _registrar_historico(self, dados, diagnostico):
        """Mantém um resumo dos últimos ciclos para dar memória temporal à IA."""
        self.historico.append({
            "ciclo": dados["ciclo"],
            "severidade": diagnostico["severidade_geral"],
            "temp": dados["temp_sensor_termico"],
            "energia": dados["energia_bateria"],
            "downlink": dados["qualidade_downlink"],
        })

    def _bloco_telemetria(self, dados):
        """Formata a telemetria como bloco legível para injetar no prompt."""
        linhas = []
        for chave, (rotulo, unidade) in telemetria.ROTULOS.items():
            linhas.append(f"- {rotulo}: {dados[chave]} {unidade}")
        return "\n".join(linhas)

    def _bloco_alertas(self, diagnostico):
        """Formata o diagnóstico de alertas para injetar no prompt."""
        if not diagnostico["alertas"]:
            return "Nenhum alerta ativo — todos os parâmetros nominais."
        partes = [f"Severidade geral: {diagnostico['severidade_geral']}"]
        for a in diagnostico["alertas"]:
            partes.append(f"- [{a['nivel']}] {a['mensagem']}")
        if diagnostico["acoes_automaticas"]:
            partes.append("Respostas automáticas já acionadas pelo sistema:")
            for acao in diagnostico["acoes_automaticas"]:
                partes.append(f"- {acao}")
        return "\n".join(partes)

    def _bloco_historico(self):
        """Resume os ciclos anteriores (exceto o atual) para contexto temporal."""
        if len(self.historico) <= 1:
            return "Sem ciclos anteriores registrados nesta sessão."
        partes = []
        for h in list(self.historico)[:-1]:
            partes.append(
                f"- Ciclo #{h['ciclo']}: {h['severidade']} "
                f"(temp {h['temp']}°C, energia {h['energia']}%, "
                f"downlink {h['downlink']}%)"
            )
        return "\n".join(partes)

    def _montar_prompt(self, pergunta, dados, diagnostico):
        """Constrói o prompt final com dados, alertas, histórico e a pergunta."""
        return (
            f"## TELEMETRIA ATUAL — EnviroSat (Ciclo #{dados['ciclo']}, "
            f"{dados['timestamp']})\n"
            f"Região observada: {dados['regiao_observada']}\n"
            f"{self._bloco_telemetria(dados)}\n\n"
            f"## DIAGNÓSTICO DOS ALERTAS (calculado em Python)\n"
            f"{self._bloco_alertas(diagnostico)}\n\n"
            f"## HISTÓRICO RECENTE (memória de contexto)\n"
            f"{self._bloco_historico()}\n\n"
            f"## PERGUNTA DO OPERADOR\n{pergunta}\n\n"
            f"Responda seguindo rigorosamente o formato e as regras do seu "
            f"system prompt, sempre amarrando a análise técnica ao impacto "
            f"terrestre para o setor ambiental."
        )
