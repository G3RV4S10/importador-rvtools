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
    Ex: 'vHost_tags_Afinidade_GH' é renomeado para 'vHost_tags_AFINIDADE_GH'
    Adicionar novas colunas ao dicionário conforme necessário.
    Seguir o padrão: chave em minúsculas -> valor com o nome correto
    Args:
        df (pd.DataFrame): DataFrame cujas colunas serão normalizadas.
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
def insert_host(cur, h: Dict[str, Any], ts: datetime) -> int:
    sql = """
        INSERT INTO hosts (
            vHostName, vHostDatacenter, vHostCluster, vHostCpuModel, vHostCpuMhz,
            vHostvCPUs, vHostvRAM, vHostVMUsedMemory,
            vHostNumCpu, vHostCoresPerCPU, vHostNumCpuCores, vHostMemorySize,
            vHostFullName, vHostVendor, vHostModel, vHost_tags_AFINIDADE_GH, vHostVISDKServer,
            vHostVMsTotal, vHostVMs, data_rvtools
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    params = (
        to_str(h.get('vHostName')),
        to_str(h.get('vHostDatacenter')), 
        to_str(h.get('vHostCluster')),
        to_str(h.get('vHostCpuModel')),
        to_int(h.get('vHostCpuMhz')),
        to_int(h.get('vHostvCPUs')),
        to_int(h.get('vHostvRAM')),
        to_int(h.get('vHostVMUsedMemory')),
        to_int(h.get('vHostNumCpu')),
        to_int(h.get('vHostCoresPerCPU')),
        to_int(h.get('vHostNumCpuCores')),
        to_int(h.get('vHostMemorySize')),
        to_str(h.get('vHostFullName')),
        to_str(h.get('vHostVendor')),
        to_str(h.get('vHostModel')),
        to_str(h.get('vHost_tags_AFINIDADE_GH')),
        to_str(h.get('vHostVISDKServer')),
        to_int(h.get('vHostVMsTotal')),
        to_int(h.get('vHostVMs')),
        ts,
    )
    cur.execute(sql, params)
    return cur.lastrowid


def insert_vm(cur, v: Dict[str, Any], host_id: Optional[int], ts: datetime) -> int:
    sql = """
        INSERT INTO vms (
            vInfoVMName, vInfoGuestHostName, vInfoDataCenter, vInfoCluster,
            vInfoPowerstate, vInfoTemplate, vInfoProvisioned, vInfoInUse,
            vInfoCPUs, vInfoMemory, vInfoNICs, vInfoNumVirtualDisks,
            vInfoTotalDiskCapacityMiB, vInfoVideoRamKiB, vInfoOS, vInfoOSTools,
            vInfoVISDKServerType, vInfoVISDKServer, host_id, data_rvtools
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    params = (
        to_str(v.get('vInfoVMName')),
        to_str(v.get('vInfoGuestHostName')),
        to_str(v.get('vInfoDataCenter')),
        to_str(v.get('vInfoCluster')),
        to_str(v.get('vInfoPowerstate')),
        to_str(v.get('vInfoTemplate')),
        to_int(v.get('vInfoProvisioned')),
        to_int(v.get('vInfoInUse')),
        to_int(v.get('vInfoCPUs')),
        to_int(v.get('vInfoMemory')),
        to_int(v.get('vInfoNICs')),
        to_int(v.get('vInfoNumVirtualDisks')),
        to_int(v.get('vInfoTotalDiskCapacityMiB')),
        to_int(v.get('vInfoVideoRamKiB')),
        to_str(v.get('vInfoOS')),
        to_str(v.get('vInfoOSTools')),
        to_str(v.get('vInfoVISDKServerType')),
        to_str(v.get('vInfoVISDKServer')),
        host_id,
        ts.date(),
    )
    cur.execute(sql, params)
    return cur.lastrowid


# =========================
# Leitura de planilhas
# =========================
VHOST_COLS = [
    'vHostName', 'vHostDatacenter', 'vHostCluster', 'vHostCpuModel', 'vHostCpuMhz',
    'vHostvCPUs', 'vHostvRAM', 'vHostVMUsedMemory',
    'vHostNumCpu', 'vHostCoresPerCPU', 'vHostNumCpuCores', 'vHostMemorySize',
    'vHostFullName', 'vHostVendor', 'vHostModel', 'vHost_tags_AFINIDADE_GH', 'vHostVISDKServer',
    'vHostVMsTotal', 'vHostVMs',
]

VINFO_COLS = [
    'vInfoVMName', 'vInfoGuestHostName', 'vInfoDataCenter', 'vInfoCluster',
    'vInfoPowerstate', 'vInfoTemplate', 'vInfoProvisioned', 'vInfoInUse',
    'vInfoCPUs', 'vInfoMemory', 'vInfoNICs',
    'vInfoNumVirtualDisks', 'vInfoTotalDiskCapacityMiB', 'vInfoVideoRamKiB',
    'vInfoOS', 'vInfoOSTools', 'vInfoVISDKServerType', 'vInfoVISDKServer',
    'vInfoHost',
]


def ler_sheet(path: str, sheet: str, cols: list) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, sheet_name=sheet, engine='openpyxl')
        # <<< PASSO 2: CHAMADA DA FUNÇÃO normalizar_nomes_colunas ADICIONADA AQUI
        normalizar_nomes_colunas(df)
    except ValueError:
        return pd.DataFrame(columns=cols)
    
    for c in cols:
        if c not in df.columns:
            df[c] = None
    return df[cols].copy()


# =========================
# Pipeline por arquivo
# =========================
def importar_arquivo(file_path: str):
    ts = extrair_data_do_arquivo(file_path)
    if not ts:
        print(f"[AVISO] Data não encontrada no nome do arquivo: {file_path}")
        return

    vhost_df = ler_sheet(file_path, 'vHost', VHOST_COLS)
    vinfo_df = ler_sheet(file_path, 'vInfo', VINFO_COLS)

    conn = connect_db()
    cur = conn.cursor()
    try:
        host_id_by_key: Dict[Tuple[str, str], int] = {}

        # 1) Hosts
        for _, row in vhost_df.iterrows():
            h_name = to_str(row['vHostName'])
            h_vsdk = to_str(row['vHostVISDKServer'])
            if not h_name or not h_vsdk:
                continue

            host_attrs = {col: row[col] for col in VHOST_COLS}
            host_id = insert_host(cur, host_attrs, ts)
            host_id_by_key[(h_name, h_vsdk)] = host_id

        # 2) VMs
        if not vinfo_df.empty:
            for _, row in vinfo_df.iterrows():
                vm_name = to_str(row['vInfoVMName'])
                vm_vsdk = to_str(row['vInfoVISDKServer'])
                
                if not vm_name or not vm_vsdk:
                    continue

                vinfo_host = to_str(row['vInfoHost'])
                host_id = host_id_by_key.get((vinfo_host, vm_vsdk))
                
                if not host_id:
                    host_id = None

                vm_attrs = {col: row[col] for col in VINFO_COLS if col != 'vInfoHost'}
                insert_vm(cur, vm_attrs, host_id, ts)

        conn.commit()
        print(f"[OK] Importação concluída: {os.path.basename(file_path)}")
        
        renomear_para_processado(file_path)

    except Exception as e:
        conn.rollback()
        print(f"[ERRO] Falha ao importar {os.path.basename(file_path)}: {e}")
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
        importar_arquivo(arquivo)


# =========================
# Execução
# =========================
if __name__ == "__main__":
    diretorio = os.getenv('PLAN_DIR', 'C:/Users/diego.gervasio/Downloads/rvtools')
    processar_planilhas(diretorio)
    print("\nProcessamento finalizado.")
