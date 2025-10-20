import pandas as pd
import glob
import re
from datetime import datetime

def extrair_data_do_arquivo(nome_arquivo):
    """Extrai a data do nome do arquivo no formato v141p500_06062024.xlsx."""
    match = re.search(r'(\d{2})(\d{2})(\d{4})', nome_arquivo)
    if match:
        return datetime.strptime(match.group(0), '%d%m%Y').date()
    return None

def contar_hosts_em_planilhas(diretorio_planilhas):
    """Conta o número total de Hosts em todas as planilhas no diretório."""
    arquivos = glob.glob(f"{diretorio_planilhas}/*.xlsx")
    total_hosts = 0

    for arquivo in arquivos:
        print(f"Processando {arquivo}...")
        try:
            # Lê a aba 'vHost' da planilha
            vhost_df = pd.read_excel(arquivo, sheet_name='vHost')
            
            # Conta o número de linhas (um VM por linha)
            total_hosts += len(vhost_df)
        except Exception as e:
            print(f"Erro ao processar {arquivo}: {e}")
    
    return total_hosts

# Substitua pelo caminho do diretório onde os arquivos Excel estão localizados
diretorio_planilhas = "C:/Users/diego.gervasio/Desktop/vcenter"

# Chama a função e exibe o total de Hosts
total_hosts = contar_hosts_em_planilhas(diretorio_planilhas)
print(f"Número total de Hosts em todas as planilhas: {total_hosts}")
