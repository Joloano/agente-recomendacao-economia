import agente_energia as agente

TOLERANCIA = 0.001


def preparar(residencia_id):
    registros = agente.carregar_dataset(agente.CAMINHO_DATASET)
    residencia = agente.selecionar_residencia(registros, residencia_id)
    percepcao = agente.perceber(residencia)
    estado = agente.criar_estado(percepcao)
    for equipamento in agente.identificar_elegiveis(percepcao["equipamentos"]):
        estado["pendentes"].append(equipamento["equipamento_id"])
    return percepcao, estado


def iguais(obtido, esperado):
    if isinstance(esperado, float):
        return abs(obtido - esperado) < TOLERANCIA
    return obtido == esperado


def casos_decisao():
    casos = []
    registros = agente.carregar_dataset(agente.CAMINHO_DATASET)
    for numero in range(1, 11):
        residencia_id = f"R{numero:02d}"
        residencia = agente.selecionar_residencia(registros, residencia_id)
        percepcao = agente.perceber(residencia)
        elegiveis = agente.identificar_elegiveis(percepcao["equipamentos"])
        casos.append({
            "descricao": f"{residencia_id} tem 3 elegíveis",
            "obtido": len(elegiveis),
            "esperado": 3,
        })

    percepcao, estado = preparar("R02")
    recomendacoes = agente.ordenar_recomendacoes(agente.gerar_recomendacoes(estado, percepcao))
    esperadas = [("E05", 4.30), ("E04", 4.10), ("E06", 3.30)]
    for posicao, (equipamento_id, utilidade) in enumerate(esperadas):
        recomendacao = recomendacoes[posicao]
        casos.append({
            "descricao": f"R02: {posicao + 1}º lugar é {equipamento_id}",
            "obtido": recomendacao["oportunidade"]["equipamento_id"],
            "esperado": equipamento_id,
        })
        casos.append({
            "descricao": f"R02: utilidade de {equipamento_id} é {utilidade:.2f}",
            "obtido": recomendacao["utilidade"],
            "esperado": utilidade,
        })
    return casos


def casos_feedback():
    casos = []
    percepcao, estado = preparar("R02")
    oportunidades = {}
    for oportunidade in agente.identificar_elegiveis(percepcao["equipamentos"]):
        oportunidades[oportunidade["equipamento_id"]] = oportunidade
    tv = oportunidades["E05"]
    computador = oportunidades["E06"]

    agente.registrar_feedback(estado, tv, "aceitar")
    casos.append({"descricao": "Aceitar a TV reduz o consumo para 16.743",
                  "obtido": estado["consumo_estimado_kwh"], "esperado": 16.743})
    casos.append({"descricao": "A TV sai das pendentes",
                  "obtido": "E05" in estado["pendentes"], "esperado": False})

    agente.registrar_feedback(estado, computador, "rejeitar")
    casos.append({"descricao": "Rejeitar o Computador mantém 16.743",
                  "obtido": estado["consumo_estimado_kwh"], "esperado": 16.743})
    casos.append({"descricao": "Pendentes ficam só com E04",
                  "obtido": estado["pendentes"], "esperado": ["E04"]})

    repetido = agente.registrar_feedback(estado, tv, "aceitar")
    casos.append({"descricao": "Aceitar a TV de novo é recusado",
                  "obtido": repetido, "esperado": False})
    casos.append({"descricao": "Sem desconto duplicado",
                  "obtido": estado["consumo_estimado_kwh"], "esperado": 16.743})

    estado["consumo_estimado_kwh"] = 0.05
    agente.atualizar_consumo(estado, 0.12)
    casos.append({"descricao": "Consumo nunca fica negativo",
                  "obtido": estado["consumo_estimado_kwh"], "esperado": 0.0})
    return casos


def casos_desempate():
    percepcao, estado = preparar("R07")
    recomendacoes = agente.ordenar_recomendacoes(agente.gerar_recomendacoes(estado, percepcao))
    ordem = []
    for recomendacao in recomendacoes:
        ordem.append(recomendacao["oportunidade"]["equipamento_id"])
    return [
        {"descricao": "R07: Máquina de lavar tem utilidade 4.10",
         "obtido": recomendacoes[1]["utilidade"], "esperado": 4.10},
        {"descricao": "R07: Ventilador também tem 4.10 (empate)",
         "obtido": recomendacoes[2]["utilidade"], "esperado": 4.10},
        {"descricao": "R07: desempate pela economia: TV, Máquina, Ventilador",
         "obtido": ordem, "esperado": ["E05", "E04", "E06"]},
    ]


def executar_testes():
    casos = casos_decisao() + casos_feedback() + casos_desempate()
    acertos = 0
    print("TESTES AUTOMÁTICOS")
    for numero, caso in enumerate(casos, start=1):
        if iguais(caso["obtido"], caso["esperado"]):
            acertos += 1
            situacao = "OK"
        else:
            situacao = f"FALHOU (obtido {caso['obtido']}, esperado {caso['esperado']})"
        print(f"{numero:2d}. {caso['descricao']}: {situacao}")
    print(f"RESUMO: {acertos} de {len(casos)} testes OK")
    return acertos == len(casos)


if __name__ == "__main__":
    executar_testes()
