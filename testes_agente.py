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


if __name__ == "__main__":
    for caso in casos_decisao():
        print(caso["descricao"], iguais(caso["obtido"], caso["esperado"]))
