# -*- coding: utf-8 -*-

import os
import re
import glob
from datetime import datetime
from typing import Optional, Dict, Tuple, Any

import pandas as pd
import mysql.connector


# =========================
# Configuração
# =========================
DB_CONFIG = {
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASS', 'Lab2024!'),
    'host': os.getenv('DB_HOST', '192.168.255.106'),
    'database': os.getenv('DB_NAME', 'vcenter_dataprev'),
    'port': int(os.getenv('DB_PORT', '3306')),
    'autocommit': False,
}


# =========================
# Utilitários
# =========================
def extrair_data_do_arquivo(caminho: str) -> Optional[datetime]:
    base = os.path.splitext(os.path.basename(caminho))[0]
    m = re.search(r'(\d{2})(\d{2})(\d{4})$', base)
    if not m:
        m = re.search(r'(\d{2})(\d{2})(\d{4})', base)
        if not m:
            return None
    d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return datetime(y, mth, d, 0, 0, 0)


def to_int(v, default=0) -> int:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return default
        if isinstance(v, (int, float)):
            return int(float(v))
        
        s = str(v).strip()
        if s == '':
            return default

        # bloco para tratar 'True'/'False' ---
        s_lower = s.lower()
        if s_lower == 'true':
            return 1
        if s_lower == 'false':
            return 0
        # --- FIM DO BLOCO ---
 
        s = s.replace('.', '').replace(',', '.')
        return int(float(s))
    except Exception:
        return default


def to_str(v, default='') -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return default
    return str(v).strip()


def connect_db():
    return mysql.connector.connect(**DB_CONFIG)


def renomear_para_processado(file_path: str):
    try:
        if not os.path.exists(file_path):
            print(f"[AVISO] Arquivo não encontrado para renomear: {file_path}")
            return
        
        base, ext = os.path.splitext(file_path)
        novo_nome = f"{base}_PROCESSADO{ext}"
        
        os.rename(file_path, novo_nome)
        print(f"[INFO] Arquivo renomeado para: {os.path.basename(novo_nome)}")
    except OSError as e:
        print(f"[ERRO] Falha ao renomear o arquivo {os.path.basename(file_path)}: {e}")

# <<< FUNÇÃO PARA NORMALIZAR COLUNA DE Afinidade >>>
def normalizar_nomes_colunas(df: pd.DataFrame):
    """
    Normaliza nomes de colunas que podem ter variações de maiúsculas/minúsculas.
    """
    mapeamento_colunas = {
        'vhost_tags_afinidade_gh': 'vHost_tags_AFINIDADE_GH'
    }

    colunas_para_renomear = {}
    for col in df.columns:
        col_lower = str(col).lower()
        if col_lower in mapeamento_colunas and col != mapeamento_colunas[col_lower]:
            colunas_para_renomear[col] = mapeamento_colunas[col_lower]
            
    if colunas_para_renomear:
        df.rename(columns=colunas_para_renomear, inplace=True)
        print(f"[INFO] Colunas normalizadas: {colunas_para_renomear}")


# =========================
# Funções de Inserção
# =========================

# Função para inserir informações de rede.
def insert_network(cur, n: Dict[str, Any], vm_id: Optional[int], ts: datetime) -> int:
    sql = """
        INSERT INTO networks (
            vNetworkVMName, vNetworkPowerstate, vNetworkNic, vNetworkAdapter, vNetworkName, vNetworkSwitch, vNetworkConnected, vNetworkIP4Address,
            vNetworkDirectPathIO, vNetworkDatacenter, vNetworkCluster, vNetworkHost, vNetworkFolder, vNetworkVISDKServer, data_rvtools
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    
    params = (
        to_str(n.get('vNetworkVMName')),
        to_str(n.get('vNetworkPowerstate')),
        to_str(n.get('vNetworkNic')),
        to_str(n.get('vNetworkAdapter')),
        to_str(n.get('vNetworkName')),
        to_str(n.get('vNetworkSwitch')),
        # --- CORREÇÃO 2: Usar to_int para a coluna booleana ---
        to_int(n.get('vNetworkConnected')),
        # --- FIM DI BLOCO ---
        to_str(n.get('vNetworkIP4Address')),
        # --- INT, OTRO BOLEAN --- 
        to_int(n.get('vNetworkDirectPathIO')),
        # --- FIM DO BLOCO --- 
        to_str(n.get('vNetworkDatacenter')),
        to_str(n.get('vNetworkCluster')),
        to_str(n.get('vNetworkHost')),
        to_str(n.get('vNetworkFolder')),
        to_str(n.get('vNetworkVISDKServer')),
        ts.date(),
    )
    cur.execute(sql, params)
    return cur.lastrowid

# =========================
# Leitura de planilhas
# =========================

VNETWORK_COLS = [
    'vNetworkVMName', 'vNetworkPowerstate', 'vNetworkNic', 'vNetworkAdapter', 'vNetworkName', 'vNetworkSwitch', 'vNetworkConnected', 'vNetworkIP4Address',
    'vNetworkDirectPathIO', 'vNetworkDatacenter', 'vNetworkCluster', 'vNetworkHost', 'vNetworkFolder', 'vNetworkVISDKServer',
]


def ler_sheet(path: str, sheet: str, cols: list) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, sheet_name=sheet, engine='openpyxl')
        #CHAMADA DA FUNÇÃO normalizar_nomes_colunas ADICIONADA AQUI
        normalizar_nomes_colunas(df)
    except ValueError:
        print(f"[AVISO] Aba '{sheet}' não encontrada em {os.path.basename(path)}")
        return pd.DataFrame(columns=cols)
    
    for c in cols:
        if c not in df.columns:
            print(f"[AVISO] Coluna esperada '{c}' não encontrada na aba '{sheet}'. Será preenchida com None.")
            df[c] = None
    return df[cols].copy()


# =========================
# Pipeline por arquivo
# =========================
def importar_arquivo_vnetwork(file_path: str):
    ts = extrair_data_do_arquivo(file_path)
    if not ts:
        print(f"[AVISO] Data não encontrada no nome do arquivo: {file_path}")
        return

    # Lê apenas a aba vNetwork
    vnetwork_df = ler_sheet(file_path, 'vNetwork', VNETWORK_COLS)

    if vnetwork_df.empty:
        print(f"[AVISO] Nenhum dado encontrado na aba 'vNetwork' do arquivo: {file_path}")
        return

    conn = connect_db()
    cur = conn.cursor()
    try:
        # 1) Redes
        print(f"[INFO] Processando {len(vnetwork_df)} registros da aba vNetwork...")
        for _, row in vnetwork_df.iterrows():
            network_vm_name = to_str(row['vNetworkVMName'])
            network_vsdk = to_str(row['vNetworkVISDKServer'])

            if not network_vm_name or not network_vsdk:
                print(f"[AVISO] Registro de rede pulado por falta de 'vNetworkVMName' ou 'vNetworkVISDKServer'.")
                continue

            network_attrs = {col: row[col] for col in VNETWORK_COLS}
            
            # Passa None para o vm_id, pois não estamos processando as VMs para obter o ID
            insert_network(cur, network_attrs, None, ts)

        conn.commit()
        print(f"[OK] Importação da 'vNetwork' concluída: {os.path.basename(file_path)}")
        
        renomear_para_processado(file_path)

    except Exception as e:
        conn.rollback()
        print(f"[ERRO] Falha ao importar 'vNetwork' de {os.path.basename(file_path)}: {e}")
    finally:
        cur.close()
        conn.close()


# =========================
# Lote de planilhas
# =========================
def processar_planilhas(diretorio_raiz: str):
    padrao_busca = os.path.join(diretorio_raiz, "**", "*.xlsx")
    all_files = glob.glob(padrao_busca, recursive=True)
    arquivos = sorted([f for f in all_files if '_PROCESSADO' not in os.path.basename(f)])
    
    if not arquivos:
        print(f"[AVISO] Nenhum arquivo .xlsx novo para processar em: {diretorio_raiz} e suas subpastas.")
        return
        
    for arquivo in arquivos:
        print(f"\n[INFO] Processando: {arquivo}")
        importar_arquivo_vnetwork(arquivo) # Chama a função específica


# =========================
# Execução
# =========================
if __name__ == "__main__":
    diretorio = os.getenv('PLAN_DIR', 'C:/Users/diego.gervasio/Downloads/rvtools')
    processar_planilhas(diretorio)
    print("\nProcessamento finalizado.")