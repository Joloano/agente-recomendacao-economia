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

if __name__ == "__main__":
    registros = carregar_dataset(CAMINHO_DATASET)
    residencia = selecionar_residencia(registros, RESIDENCIA_SELECIONADA)

    if len(residencia) == 0:
        print(f"Residência {RESIDENCIA_SELECIONADA} não encontrada no dataset.")
    else:
        print(f"Residência {RESIDENCIA_SELECIONADA}: {len(residencia)} equipamentos carregados.")