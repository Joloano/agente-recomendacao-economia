# Trabalho 2 - Agente inteligente para recomendação de economia de energia
# Agentes Inteligentes para Sistemas Web

#um agente so funciona se souber aonde estao os dados e qual residencia ele vai analisar

CAMINHO_DATASET = "dados/dataset_consumo_energia.csv"
RESIDENCIA_SELECIONADA = "R02"

#teste de caminho

arquivo = open(CAMINHO_DATASET, encoding="utf-8")
print(arquivo.readline())
arquivo.close()
print(f"Residência selecionada: {RESIDENCIA_SELECIONADA}")
