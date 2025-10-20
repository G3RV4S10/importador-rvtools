from pathlib import Path
import pandas as pd

# Configurações
pasta_entrada = Path("entrada")  # diretorio com os arquivos excel(.xls)
arquivos = sorted(pasta_entrada.glob("*.xls"))

# Quais abas juntar primeiro e depois
abas_primeiro_lote = ["Aba1", "Aba2"]  # trocar pelos nomes reais
abas_segundo_lote = ["Aba3"]           # trocar pelos nomes reais

dfs_lote1 = []
for arq in arquivos:
    # Lê apenas as abas desejadas; pandas escolhe engine por extensão (xls -> xlrd)
    lidas = pd.read_excel(arq, sheet_name=abas_primeiro_lote)  # dict: nome_aba -> DataFrame
    for nome_aba, df in lidas.items():
        df["arquivo"] = arq.name
        df["aba"] = nome_aba
        dfs_lote1.append(df)

unificado_lote1 = pd.concat(dfs_lote1, ignore_index=True)

# EXEMPLOS de cálculos (ajuste para suas colunas)
# 1) Nova coluna
if {"Qtd", "Preco"}.issubset(unificado_lote1.columns):
    unificado_lote1["Total"] = unificado_lote1["Qtd"] * unificado_lote1["Preco"]

# 2) Agregação
agrupado = None
if {"Categoria", "Total"}.issubset(unificado_lote1.columns):
    agrupado = (unificado_lote1
                .groupby("Categoria", as_index=False, dropna=False)["Total"]
                .sum())

# Opcional: processar o segundo lote de abas específicas
dfs_lote2 = []
for arq in arquivos:
    lidas2 = pd.read_excel(arq, sheet_name=abas_segundo_lote)
    for nome_aba, df in lidas2.items():
        df["arquivo"] = arq.name
        df["aba"] = nome_aba
        dfs_lote2.append(df)

unificado_lote2 = pd.concat(dfs_lote2, ignore_index=True) if dfs_lote2 else None

# Exporta para um só Excel, com múltiplas abas
saida = Path("saida")
saida.mkdir(exist_ok=True)
with pd.ExcelWriter(saida / "resultado.xlsx") as writer:
    unificado_lote1.to_excel(writer, sheet_name="Unificado_Lote1", index=False)
    if agrupado is not None:
        agrupado.to_excel(writer, sheet_name="Totais_Lote1", index=False)
    if unificado_lote2 is not None:
        unificado_lote2.to_excel(writer, sheet_name="Unificado_Lote2", index=False)
