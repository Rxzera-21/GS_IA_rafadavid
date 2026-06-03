"""Thresholds e regras de decisão — Trilha EnviroSat.

Toda a lógica de decisão "é crítico ou não" vive AQUI, em Python — não no prompt
da IA. A IA serve para explicar e contextualizar; quem decide a severidade é o
código (requisito da Frente 4 da rubrica).

Cada regra avalia um parâmetro da telemetria, classifica a severidade e, quando
aplicável, dispara uma RESPOSTA AUTOMATIZADA (ex.: ativar modo economia de
energia). A função pública é `avaliar(dados)`.
"""

# Níveis de severidade, do mais brando ao mais grave.
NOMINAL = "NOMINAL"
ATENCAO = "ATENÇÃO"
CRITICO = "CRÍTICO"

# Ordem de gravidade para calcular a severidade geral da missão.
_ORDEM = {NOMINAL: 0, ATENCAO: 1, CRITICO: 2}

# Emoji por severidade (usado na formatação do terminal).
ICONE = {NOMINAL: "🟢", ATENCAO: "🟡", CRITICO: "🔴"}


def _classificar(valor, limite_atencao, limite_critico, maior_pior=True):
    """Classifica um valor em NOMINAL/ATENÇÃO/CRÍTICO.

    maior_pior=True  -> valores ALTOS são ruins (ex.: temperatura, buffer).
    maior_pior=False -> valores BAIXOS são ruins (ex.: energia, downlink).
    """
    if maior_pior:
        if valor >= limite_critico:
            return CRITICO
        if valor >= limite_atencao:
            return ATENCAO
        return NOMINAL
    else:
        if valor <= limite_critico:
            return CRITICO
        if valor <= limite_atencao:
            return ATENCAO
        return NOMINAL


def avaliar(dados):
    """Avalia a telemetria e retorna um diagnóstico estruturado.

    Retorna um dict com:
        - severidade_geral : a pior severidade encontrada
        - alertas          : lista de alertas (parâmetro, valor, nível, mensagem)
        - acoes_automaticas: respostas automatizadas disparadas pelo código
    """
    alertas = []
    acoes = []

    # --- Regra 1: temperatura do sensor térmico ------------------------------
    temp = dados["temp_sensor_termico"]
    nivel = _classificar(temp, limite_atencao=60.0, limite_critico=75.0,
                          maior_pior=True)
    if nivel != NOMINAL:
        alertas.append({
            "parametro": "temp_sensor_termico",
            "valor": temp, "unidade": "°C", "nivel": nivel,
            "mensagem": f"Temperatura do sensor térmico em {temp}°C."
        })
        if nivel == CRITICO:
            # Resposta automatizada: reduzir duty cycle do sensor para protegê-lo.
            acoes.append("Acionado RESFRIAMENTO PASSIVO: duty cycle do sensor "
                         "térmico reduzido para 40% até estabilização.")

    # --- Regra 2: energia da bateria (modo economia) -------------------------
    energia = dados["energia_bateria"]
    nivel = _classificar(energia, limite_atencao=30.0, limite_critico=20.0,
                         maior_pior=False)
    if nivel != NOMINAL:
        alertas.append({
            "parametro": "energia_bateria",
            "valor": energia, "unidade": "%", "nivel": nivel,
            "mensagem": f"Energia disponível em {energia}%."
        })
        if nivel == CRITICO:
            # Resposta automatizada clássica do enunciado: modo economia.
            acoes.append("Ativado MODO ECONOMIA DE ENERGIA: payloads não "
                         "essenciais desligados; apenas housekeeping ativo.")

    # --- Regra 3: qualidade do downlink (comunicação) ------------------------
    downlink = dados["qualidade_downlink"]
    nivel = _classificar(downlink, limite_atencao=50.0, limite_critico=30.0,
                         maior_pior=False)
    if nivel != NOMINAL:
        alertas.append({
            "parametro": "qualidade_downlink",
            "valor": downlink, "unidade": "%", "nivel": nivel,
            "mensagem": f"Qualidade do downlink em {downlink}%."
        })
        if nivel == CRITICO:
            acoes.append("PERDA DE COMUNICAÇÃO: agendado re-downlink na próxima "
                         "passagem sobre a estação de Cuiabá; imagens retidas em buffer.")

    # --- Regra 4: buffer de imagens não transmitidas -------------------------
    buffer = dados["buffer_imagens"]
    nivel = _classificar(buffer, limite_atencao=80.0, limite_critico=92.0,
                         maior_pior=True)
    if nivel != NOMINAL:
        alertas.append({
            "parametro": "buffer_imagens",
            "valor": buffer, "unidade": "%", "nivel": nivel,
            "mensagem": f"Buffer de imagens com {buffer}% de ocupação."
        })
        if nivel == CRITICO:
            acoes.append("RISCO DE PERDA DE DADOS: priorizada compressão de "
                         "imagens antigas e downlink emergencial do buffer.")

    # --- Regra 5: erro de geolocalização -------------------------------------
    erro_geo = dados["erro_geolocalizacao"]
    nivel = _classificar(erro_geo, limite_atencao=25.0, limite_critico=40.0,
                         maior_pior=True)
    if nivel != NOMINAL:
        alertas.append({
            "parametro": "erro_geolocalizacao",
            "valor": erro_geo, "unidade": "m", "nivel": nivel,
            "mensagem": f"Erro de geolocalização em {erro_geo} m."
        })

    # --- Regra 6: saúde do sensor óptico RGB+NIR -----------------------------
    optico = dados["sensor_optico_rgb_nir"]
    nivel = _classificar(optico, limite_atencao=70.0, limite_critico=50.0,
                         maior_pior=False)
    if nivel != NOMINAL:
        alertas.append({
            "parametro": "sensor_optico_rgb_nir",
            "valor": optico, "unidade": "%", "nivel": nivel,
            "mensagem": f"Saúde do sensor óptico RGB+NIR em {optico}%."
        })

    # --- Severidade geral da missão ------------------------------------------
    if alertas:
        severidade_geral = max(alertas, key=lambda a: _ORDEM[a["nivel"]])["nivel"]
    else:
        severidade_geral = NOMINAL

    return {
        "severidade_geral": severidade_geral,
        "alertas": alertas,
        "acoes_automaticas": acoes,
    }


def resumo_textual(diagnostico):
    """Formata o diagnóstico de avaliar() em texto legível para o terminal."""
    linhas = []
    sev = diagnostico["severidade_geral"]
    linhas.append(f"{ICONE[sev]} Severidade geral: {sev}")

    if not diagnostico["alertas"]:
        linhas.append("Todos os parâmetros dentro da faixa nominal. ✓")
        return "\n".join(linhas)

    linhas.append("\nAlertas ativos:")
    for a in diagnostico["alertas"]:
        linhas.append(f"  {ICONE[a['nivel']]} [{a['nivel']}] {a['mensagem']}")

    if diagnostico["acoes_automaticas"]:
        linhas.append("\nRespostas automáticas acionadas pelo sistema:")
        for acao in diagnostico["acoes_automaticas"]:
            linhas.append(f"  ⚙️  {acao}")

    return "\n".join(linhas)
