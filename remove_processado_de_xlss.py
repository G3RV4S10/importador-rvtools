# -*- coding: utf-8 -*-

import os
import glob

def remover_processado_dos_nomes(diretorio_raiz: str):
    """
    Percorre o diretório raiz e seus subdiretórios em busca de arquivos
    que contenham '_PROCESSADO' em seu nome e os renomeia, removendo
    essa marcação.

    Args:
        diretorio_raiz (str): O caminho para o diretório inicial da busca.
    """
    padrao_busca = os.path.join(diretorio_raiz, "**", "*_PROCESSADO*")
    
    # O recursive=True faz com que a busca inclua subpastas
    arquivos_processados = glob.glob(padrao_busca, recursive=True)

    if not arquivos_processados:
        print(f"[AVISO] Nenhum arquivo com a marca '_PROCESSADO' foi encontrado em '{diretorio_raiz}' e suas subpastas.")
        return

    print(f"[INFO] Encontrados {len(arquivos_processados)} arquivos para renomear.")

    for caminho_antigo in arquivos_processados:
        # Garante que estamos tratando de um arquivo e não de um diretório
        if not os.path.isfile(caminho_antigo):
            continue

        try:
            # Remove a string "_PROCESSADO" do nome do arquivo
            novo_nome = os.path.basename(caminho_antigo).replace("_PROCESSADO", "")
            diretorio_do_arquivo = os.path.dirname(caminho_antigo)
            caminho_novo = os.path.join(diretorio_do_arquivo, novo_nome)

            # Renomeia o arquivo
            os.rename(caminho_antigo, caminho_novo)
            
            print(f"[OK] Renomeado: '{os.path.basename(caminho_antigo)}' -> '{novo_nome}'")

        except OSError as e:
            print(f"[ERRO] Falha ao renomear o arquivo '{os.path.basename(caminho_antigo)}': {e}")


# =========================
# Execução
# =========================
if __name__ == "__main__":
    # Define o diretório onde a busca começará.
    # Altere este valor para o caminho da sua pasta.
    diretorio_raiz = r'C:/Users/diego.gervasio/Downloads/RVTOOLS'
    
    print(f"Iniciando a busca por arquivos a serem renomeados em: '{diretorio_raiz}'")
    remover_processado_dos_nomes(diretorio_raiz)
    print("\nProcesso de renomeação finalizado.")