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


if __name__ == "__main__":
    percepcao, estado = preparar("R02")
    print(estado["pendentes"])
    print(iguais(4.3000000001, 4.30), iguais(16.743, 16.863))
