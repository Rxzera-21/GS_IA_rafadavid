"""Geração dos dados simulados de telemetria — Trilha EnviroSat.

Satélite simulado: observação ambiental com sensor térmico e óptico
(similar a Amazônia-1 / Landsat). Os parâmetros monitorados são os da trilha:

    - temp_sensor_termico   : temperatura do sensor térmico de detecção de focos (°C)
    - energia_bateria       : energia disponível no barramento (%)
    - qualidade_downlink    : qualidade do canal de downlink p/ a estação terrena (%)
    - buffer_imagens        : ocupação do buffer de imagens não transmitidas (%)
    - erro_geolocalizacao   : erro de geolocalização das imagens (metros)
    - sensor_optico_rgb_nir : saúde do sensor óptico RGB+NIR (%)

Os dados não precisam ser cientificamente exatos — apenas plausíveis e coerentes
com o cenário. A simulação evolui em ciclos (série temporal), com pequenas
oscilações em torno de um estado interno, de modo que rodar o sistema várias
vezes produz leituras diferentes mas coerentes.
"""

import json
import random
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Faixas nominais de cada parâmetro (usadas para gerar valores plausíveis).
# Os thresholds de alerta ficam em src/alertas.py — aqui é só a "física" do sat.
# ---------------------------------------------------------------------------
FAIXAS_NOMINAIS = {
    "temp_sensor_termico": (18.0, 45.0),   # °C — operação saudável do sensor térmico
    "energia_bateria": (55.0, 100.0),      # % — carga da bateria
    "qualidade_downlink": (70.0, 100.0),   # % — qualidade do enlace de descida
    "buffer_imagens": (5.0, 60.0),         # % — ocupação do buffer de bordo
    "erro_geolocalizacao": (2.0, 12.0),    # m  — erro de georreferência
    "sensor_optico_rgb_nir": (85.0, 100.0)  # % — saúde do sensor óptico
}

# Estado interno do satélite — persiste entre ciclos para dar continuidade.
# Inicia no meio de cada faixa nominal.
_estado = {
    nome: round((minimo + maximo) / 2, 1)
    for nome, (minimo, maximo) in FAIXAS_NOMINAIS.items()
}

_ciclo = 0  # contador de ciclos de telemetria desde o boot do sistema

# Cenário fixado: quando != None, coletar() devolve estes valores (sem random
# walk) até que limpar_cenario() seja chamado. Usado pelo comando /cenario da CLI
# para demonstrar alertas de forma determinística.
_cenario_fixado = None

_CAMINHO_CENARIOS = Path("data/cenarios.json")


def _passo_aleatorio(valor, minimo, maximo, volatilidade=0.06):
    """Aplica uma pequena variação (random walk) mantendo o valor na faixa.

    `volatilidade` é a fração da amplitude da faixa que o valor pode andar por ciclo.
    """
    amplitude = maximo - minimo
    delta = random.uniform(-volatilidade, volatilidade) * amplitude
    novo = valor + delta
    # Mantém dentro de uma faixa estendida (permite picos levemente fora do nominal)
    limite_inf = minimo - amplitude * 0.15
    limite_sup = maximo + amplitude * 0.15
    return round(max(limite_inf, min(limite_sup, novo)), 1)


def _montar_leitura():
    """Empacota o estado interno atual em uma leitura completa (com metadados)."""
    global _ciclo
    _ciclo += 1
    leitura = dict(_estado)
    leitura["ciclo"] = _ciclo
    leitura["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Identificação do alvo sob observação (storytelling da trilha ambiental)
    leitura["regiao_observada"] = "Amazônia Legal — Bioma Floresta Tropical"
    return leitura


def coletar():
    """Coleta uma leitura de telemetria (um ciclo) e retorna um dicionário.

    Esta é a função consumida pelo MissionEngine.analyze()/status_snapshot().
    - Se houver um cenário fixado, reaplica seus valores (sem clamp), de modo que
      o alerta permaneça estável a cada pergunta.
    - Caso contrário, avança um ciclo na série temporal (random walk).
    """
    if _cenario_fixado is not None:
        for nome in FAIXAS_NOMINAIS:
            if nome in _cenario_fixado:
                _estado[nome] = _cenario_fixado[nome]
        return _montar_leitura()

    for nome, (minimo, maximo) in FAIXAS_NOMINAIS.items():
        _estado[nome] = _passo_aleatorio(_estado[nome], minimo, maximo)
    return _montar_leitura()


def fixar_cenario(nome_cenario):
    """Fixa um cenário de data/cenarios.json para as próximas coletas.

    A partir daqui, coletar() devolve os valores do cenário (sem random walk),
    o que permite demonstrar alertas de forma determinística na CLI.
    Retorna a leitura resultante ou None se o cenário não existir.
    """
    global _cenario_fixado
    if not _CAMINHO_CENARIOS.exists():
        return None
    try:
        cenarios = json.loads(_CAMINHO_CENARIOS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    cenario = cenarios.get("cenarios", {}).get(nome_cenario)
    if cenario is None:
        return None

    _cenario_fixado = {
        nome: float(valor)
        for nome, valor in cenario.get("telemetria", {}).items()
        if nome in FAIXAS_NOMINAIS
    }
    leitura = coletar()  # já aplica os valores fixados
    leitura["cenario"] = nome_cenario
    leitura["descricao_cenario"] = cenario.get("descricao", "")
    return leitura


def limpar_cenario():
    """Remove o cenário fixado e volta ao modo dinâmico (random walk)."""
    global _cenario_fixado
    _cenario_fixado = None


def cenario_ativo():
    """Indica se há um cenário fixado no momento (None se modo dinâmico)."""
    return _cenario_fixado is not None


def listar_cenarios():
    """Retorna a lista de nomes de cenários disponíveis em data/cenarios.json."""
    if not _CAMINHO_CENARIOS.exists():
        return []
    try:
        cenarios = json.loads(_CAMINHO_CENARIOS.read_text(encoding="utf-8"))
        return list(cenarios.get("cenarios", {}).keys())
    except (json.JSONDecodeError, OSError):
        return []


# Metadados legíveis de cada parâmetro (rótulo + unidade) para a formatação.
ROTULOS = {
    "temp_sensor_termico": ("Temp. sensor térmico", "°C"),
    "energia_bateria": ("Energia da bateria", "%"),
    "qualidade_downlink": ("Qualidade do downlink", "%"),
    "buffer_imagens": ("Buffer de imagens", "%"),
    "erro_geolocalizacao": ("Erro de geolocalização", "m"),
    "sensor_optico_rgb_nir": ("Sensor óptico RGB+NIR", "%"),
}
