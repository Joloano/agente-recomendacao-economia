# Trabalho 2 - Agente inteligente para recomendação de economia de energia
# Agentes Inteligentes para Sistemas Web

# um agente so funciona se souber aonde estao os dados e qual residencia ele vai analisar


import csv

CAMINHO_DATASET = "dados/dataset_consumo_energia.csv"
RESIDENCIA_SELECIONADA = "R02"


# converter os registros certos

def converter_registro(registro):
    campos_float = [
        "meta_consumo_diario_kwh", "tarifa_base_rs_kwh",
        "peso_economia", "peso_conforto", "peso_flexibilidade", "peso_baixo_esforco",
        "potencia_kw", "horas_uso_diario", "consumo_diario_estimado_kwh",
        "economia_potencial_reducao_kwh",
    ]
    campos_int = [
        "numero_moradores", "impacto_conforto_1a5",
        "flexibilidade_reducao_uso_1a5", "esforco_1a5",
    ]
    for campo in campos_float:
        registro[campo] = float(registro[campo])
    for campo in campos_int:
        registro[campo] = int(registro[campo])
    registro["reducao_uso"] = registro["reducao_uso"] == "True"
    return registro


def carregar_dataset(caminho):
    registros = []
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        for registro in leitor:
            registros.append(converter_registro(registro))
    return registros


def selecionar_residencia(registros, residencia_id):
    selecionados = []
    for registro in registros:
        if registro["residencia_id"] == residencia_id:
            selecionados.append(registro)
    return selecionados


def perceber(registros_residencia):
    primeiro = registros_residencia[0]
    residencia = {
        "residencia_id": primeiro["residencia_id"],
        "numero_moradores": primeiro["numero_moradores"],
        "meta_consumo_diario_kwh": primeiro["meta_consumo_diario_kwh"],
        "tarifa_base_rs_kwh": primeiro["tarifa_base_rs_kwh"],
        "perfil_morador": primeiro["perfil_morador"],
    }

    pesos = {
        "economia": primeiro["peso_economia"],
        "conforto": primeiro["peso_conforto"],
        "flexibilidade": primeiro["peso_flexibilidade"],
        "baixo_esforco": primeiro["peso_baixo_esforco"],
    }
    equipamentos = []
    consumo_total = 0
    for registro in registros_residencia:
        equipamento = {
            "equipamento_id": registro["equipamento_id"],
            "equipamento": registro["equipamento"],
            "categoria": registro["categoria"],
            "potencia_kw": registro["potencia_kw"],
            "horas_uso_diario": registro["horas_uso_diario"],
            "consumo_diario_estimado_kwh": registro["consumo_diario_estimado_kwh"],
            "reducao_uso": registro["reducao_uso"],
            "essencialidade": registro["essencialidade"],
            "impacto_conforto_1a5": registro["impacto_conforto_1a5"],
            "flexibilidade_reducao_uso_1a5": registro["flexibilidade_reducao_uso_1a5"],
            "esforco_1a5": registro["esforco_1a5"],
            "economia_potencial_reducao_kwh": registro["economia_potencial_reducao_kwh"],
        }

        equipamentos.append(equipamento)
        consumo_total += registro["consumo_diario_estimado_kwh"]
    percepcao = {
        "residencia": residencia,
        "pesos": pesos,
        "equipamentos": equipamentos,
        "consumo_total_kwh": round(consumo_total, 3),
    }
    return percepcao


def validar_pesos(pesos):
    soma = 0
    for valor in pesos.values():
        soma += valor
    if abs(soma - 1) < 0.001:
        return True
    print(f"Aviso: a soma dos pesos é {soma:.3f}, deveria ser 1.")
    return False


def exibir_percepcao(percepcao):
    residencia = percepcao["residencia"]
    pesos = percepcao["pesos"]
    print(f"PERCEPÇÃO DA RESIDÊNCIA {residencia['residencia_id']}")
    print(f"Moradores: {residencia['numero_moradores']}")
    print(f"Perfil: {residencia['perfil_morador']}")
    print(f"Tarifa: R$ {residencia['tarifa_base_rs_kwh']:.2f}/kWh")
    print(f"Consumo atual: {percepcao['consumo_total_kwh']:.3f} kWh/dia")
    print(f"Meta: {residencia['meta_consumo_diario_kwh']:.2f} kWh/dia")
    print("Prioridades dos moradores:")
    for criterio, peso in pesos.items():
        print(f"  {criterio}: {peso:.0%}")


def criar_estado(percepcao):
    consumo = percepcao["consumo_total_kwh"]
    estado = {
        "residencia_id": percepcao["residencia"]["residencia_id"],
        "meta_consumo_diario_kwh": percepcao["residencia"]["meta_consumo_diario_kwh"],
        "consumo_inicial_kwh": consumo,
        "consumo_estimado_kwh": consumo,
        "apresentadas": [],
        "aceitas": [],
        "rejeitadas": [],
        "pendentes": [],
        "historico": [],
    }
    return estado


def mostrar_estado(estado):
    consumo = estado["consumo_estimado_kwh"]
    meta = estado["meta_consumo_diario_kwh"]
    falta = consumo - meta
    print(f"ESTADO DA SIMULAÇÃO - {estado['residencia_id']}")
    print(f"Consumo inicial:  {estado['consumo_inicial_kwh']:.3f} kWh/dia")
    print(f"Consumo estimado: {consumo:.3f} kWh/dia")
    if falta > 0:
        print(f"Faltam {falta:.3f} kWh/dia para atingir a meta ({meta:.2f}).")
    else:
        print(f"Meta de {meta:.2f} kWh/dia atingida!")
    print(f"Aceitas:    {', '.join(estado['aceitas']) or 'nenhuma'}")
    print(f"Rejeitadas: {', '.join(estado['rejeitadas']) or 'nenhuma'}")
    print(f"Pendentes:  {', '.join(estado['pendentes']) or 'nenhuma'}")


if __name__ == "__main__":
    registros = carregar_dataset(CAMINHO_DATASET)
    residencia = selecionar_residencia(registros, RESIDENCIA_SELECIONADA)

    if len(residencia) == 0:
        print(f"Residência {RESIDENCIA_SELECIONADA} não encontrada no dataset.")
    else:
        print(f"Residência {RESIDENCIA_SELECIONADA}: {len(residencia)} equipamentos carregados.")
        percepcao = perceber(residencia)
        validar_pesos(percepcao["pesos"])
        exibir_percepcao(percepcao)
        estado = criar_estado(percepcao)
        mostrar_estado(estado)
