# Trabalho 2 - Agente inteligente para recomendação de economia de energia
# Agentes Inteligentes para Sistemas Web

# um agente so funciona se souber aonde estao os dados e qual residencia ele vai analisar


import csv

CAMINHO_DATASET = "dados/dataset_consumo_energia.csv"
RESIDENCIA_SELECIONADA = "R02"
DESCRICOES_POR_CATEGORIA = {
    "lavanderia": "Acumular roupas e fazer lavagens com carga completa.",
    "entretenimento": "Desligar a TV quando ninguém estiver assistindo, sem deixá-la como som de fundo.",
    "trabalho_estudo": "Ativar o modo de economia de energia e desligar o computador ao fim do uso.",
    "iluminacao": "Apagar as luzes de ambientes vazios e aproveitar a luz natural.",
    "cozinha": "Planejar o uso do forno e assar mais de um alimento por vez.",
    "climatizacao": "Ligar o ventilador só com pessoas no ambiente e desligá-lo ao sair.",
}
DESCRICAO_PADRAO = "Reduzir o tempo de uso do equipamento."


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


def eh_elegivel(equipamento):
    return (
            equipamento["reducao_uso"]
            and equipamento["economia_potencial_reducao_kwh"] > 0
            and equipamento["essencialidade"] != "essencial"
            and equipamento["impacto_conforto_1a5"] <= 3
    )


def identificar_elegiveis(equipamentos):
    elegiveis = []
    for equipamento in equipamentos:
        if eh_elegivel(equipamento):
            elegiveis.append(equipamento)
    return elegiveis


def obter_maior_economia(elegiveis):
    maior = 0
    for oportunidade in elegiveis:
        economia = oportunidade["economia_potencial_reducao_kwh"]
        if economia > maior:
            maior = economia
    return maior


def calcular_notas(oportunidade, maior_economia):
    if maior_economia > 0:
        proporcao = oportunidade["economia_potencial_reducao_kwh"] / maior_economia
    else:
        proporcao = 0
    notas = {
        "economia": 1 + 4 * proporcao,
        "conforto": 6 - oportunidade["impacto_conforto_1a5"],
        "flexibilidade": oportunidade["flexibilidade_reducao_uso_1a5"],
        "baixo_esforco": 6 - oportunidade["esforco_1a5"],
    }
    return notas


def calcular_utilidade(notas, pesos):
    utilidade = 0
    for criterio, peso in pesos.items():
        utilidade += peso * notas[criterio]
    return utilidade


def gerar_recomendacoes(estado, percepcao):
    elegiveis = identificar_elegiveis(percepcao["equipamentos"])
    maior_economia = obter_maior_economia(elegiveis)
    recomendacoes = []
    for oportunidade in elegiveis:
        if oportunidade["equipamento_id"] in estado["pendentes"]:
            notas = calcular_notas(oportunidade, maior_economia)
            recomendacao = {
                "oportunidade": oportunidade,
                "notas": notas,
                "utilidade": calcular_utilidade(notas, percepcao["pesos"]),
            }
            recomendacoes.append(recomendacao)
    return recomendacoes


def chave_ordenacao(recomendacao):
    # Desempate: maior utilidade, depois maior economia (kWh), depois ordem do dataset
    utilidade = round(recomendacao["utilidade"], 6)
    economia = recomendacao["oportunidade"]["economia_potencial_reducao_kwh"]
    return (utilidade, economia)


def ordenar_recomendacoes(recomendacoes):
    return sorted(recomendacoes, key=chave_ordenacao, reverse=True)


def gerar_descricao(oportunidade):
    categoria = oportunidade["categoria"]
    return DESCRICOES_POR_CATEGORIA.get(categoria, DESCRICAO_PADRAO)


def apresentar_recomendacoes(recomendacoes, tarifa):
    print("RECOMENDAÇÕES PERSONALIZADAS (maior utilidade primeiro)")
    for posicao, recomendacao in enumerate(recomendacoes, start=1):
        oportunidade = recomendacao["oportunidade"]
        notas = recomendacao["notas"]
        economia = oportunidade["economia_potencial_reducao_kwh"]

        print(f"{posicao}. {oportunidade['equipamento']} ({oportunidade['categoria']}) "
              f"- utilidade {recomendacao['utilidade']:.2f}")
        print(f"   Economia: {economia:.3f} kWh/dia (R$ {economia * tarifa:.2f}/dia)")
        print(f"   Impacto no conforto: {oportunidade['impacto_conforto_1a5']}/5 | "
              f"Flexibilidade: {oportunidade['flexibilidade_reducao_uso_1a5']}/5 | "
              f"Esforço: {oportunidade['esforco_1a5']}/5")
        print(f"   Notas: economia {notas['economia']:.1f} | conforto {notas['conforto']} | "
              f"flexibilidade {notas['flexibilidade']} | baixo esforço {notas['baixo_esforco']}")
        print(f"   O que fazer: {gerar_descricao(oportunidade)}")


def registrar_apresentadas(estado, recomendacoes):
    for recomendacao in recomendacoes:
        equipamento_id = recomendacao["oportunidade"]["equipamento_id"]
        if equipamento_id not in estado["apresentadas"]:
            estado["apresentadas"].append(equipamento_id)


def atualizar_consumo(estado, economia):
    novo_consumo = estado["consumo_estimado_kwh"] - economia
    estado["consumo_estimado_kwh"] = round(max(0, novo_consumo), 3)


def registrar_feedback(estado, oportunidade, resposta):
    equipamento_id = oportunidade["equipamento_id"]
    nome = oportunidade["equipamento"]

    if resposta not in ("aceitar", "rejeitar"):
        print(f"Resposta inválida: '{resposta}'. Use 'aceitar' ou 'rejeitar'.")
        return False
    if equipamento_id not in estado["pendentes"]:
        print(f"{nome} já foi tratada. Nada foi alterado.")
        return False

    consumo_antes = estado["consumo_estimado_kwh"]
    if resposta == "aceitar":
        estado["aceitas"].append(equipamento_id)
        atualizar_consumo(estado, oportunidade["economia_potencial_reducao_kwh"])
    else:
        estado["rejeitadas"].append(equipamento_id)
    estado["pendentes"].remove(equipamento_id)

    estado["historico"].append({
        "equipamento_id": equipamento_id,
        "resposta": resposta,
        "consumo_antes": consumo_antes,
        "consumo_depois": estado["consumo_estimado_kwh"],
    })
    return True


def ler_escolha(quantidade):
    while True:
        texto = input(f"Escolha uma recomendação (1 a {quantidade}) ou 0 para sair: ").strip()
        if texto.isdigit():
            numero = int(texto)
            if 0 <= numero <= quantidade:
                return numero
        print(f"Entrada inválida: '{texto}'. Digite um número de 0 a {quantidade}.")

def ler_resposta():
    while True:
        texto = input("Aceitar (a) ou rejeitar (r)?  ").strip().lower()
        if texto =="a":
            return "aceitar"
        if texto =="r":
            return "rejeitar"
        print(f"Resposta inválida: '{texto}'. Digite 'a' ou 'r'.")

def mostrar_resumo(estado, tarifa):
    inicial = estado["consumo_inicial_kwh"]
    final = estado["consumo_estimado_kwh"]
    economia = round(inicial-final, 3)
    print("Resumo final")
    print(f"Consumo inicial: {inicial:.3f} kWh/dia")
    print(f"Consumo final:   {final:.3f} kWh/dia")
    print(f"Economia total:  {economia:.3f} kWh/dia "
          f"(R$ {economia * tarifa:.2f}/dia, cerca de R$ {economia * tarifa * 30:.2f}/mês)")
    print(f"Aceitas:    {', '.join(estado['aceitas']) or 'nenhuma'}")
    print(f"Rejeitadas: {', '.join(estado['rejeitadas']) or 'nenhuma'}")



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
        elegiveis = identificar_elegiveis(percepcao["equipamentos"])
        for equipamento in elegiveis:
            estado["pendentes"].append(equipamento["equipamento_id"])

        if len(elegiveis) == 0:
            print("Nenhuma oportunidade de economia elegível para esta residência.")
        else:
            print(f"{len(elegiveis)} oportunidades elegíveis encontradas.")
        mostrar_estado(estado)
        recomendacoes = gerar_recomendacoes(estado, percepcao)
        recomendacoes = ordenar_recomendacoes(recomendacoes)
        apresentar_recomendacoes(recomendacoes, percepcao["residencia"]["tarifa_base_rs_kwh"])
        registrar_apresentadas(estado, recomendacoes)
        print("Apresentadas:", ", ".join(estado["apresentadas"]))
        tv = recomendacoes[0]["oportunidade"]
        computador = recomendacoes[2]["oportunidade"]
        registrar_feedback(estado, tv, "aceitar")
        registrar_feedback(estado, computador, "rejeitar")
        registrar_feedback(estado, tv, "aceitar")  # repetido: não pode descontar de novo
        registrar_feedback(estado, tv, "talvez")  # inválido: não muda nada
        mostrar_estado(estado)
        print(estado["historico"])
        print("Resposta:", ler_resposta())
        mostrar_resumo(estado, percepcao["residencia"]["tarifa_base_rs_kwh"])
