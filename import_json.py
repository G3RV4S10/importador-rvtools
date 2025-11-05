import json
import mysql.connector
from mysql.connector import Error

# =========================
# Configuração MySQL
# =========================
DB_CONFIG = {
    'user': 'root',
    'password': 'Lab2024!',
    'host': '192.168.255.253',
    'database': 'nsx',
    'port': 3306
}

# =========================
# Conexão
# =========================
def conectar():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            print(f"✅ Conectado ao banco {DB_CONFIG['database']}")
            return conn
    except Error as e:
        print(f"❌ Erro ao conectar: {e}")
    return None


# =========================
# Criação das tabelas
# =========================
def criar_tabelas(cursor):
    tabelas = {
        "loadbalancers": """
            CREATE TABLE IF NOT EXISTS loadbalancers (
                unique_id VARCHAR(100) PRIMARY KEY,
                id VARCHAR(100),
                display_name VARCHAR(255),
                description TEXT,
                connectivity_path VARCHAR(255),
                size VARCHAR(50),
                resource_type VARCHAR(100),
                create_user VARCHAR(100),
                last_modified_user VARCHAR(100)
            )
        """,
        "virtual_servers": """
            CREATE TABLE IF NOT EXISTS virtual_servers (
                unique_id VARCHAR(100) PRIMARY KEY,
                id VARCHAR(100),
                display_name VARCHAR(255),
                ip_address VARCHAR(50),
                ports VARCHAR(100),
                lb_service_path VARCHAR(255),
                pool_path VARCHAR(255),
                description TEXT,
                create_user VARCHAR(100),
                last_modified_user VARCHAR(100)
            )
        """,
        "pools": """
            CREATE TABLE IF NOT EXISTS pools (
                unique_id VARCHAR(100) PRIMARY KEY,
                id VARCHAR(100),
                display_name VARCHAR(255),
                description TEXT,
                algorithm VARCHAR(50),
                monitor_path VARCHAR(255),
                member_count INT,
                create_user VARCHAR(100),
                last_modified_user VARCHAR(100)
            )
        """
    }

    for nome, sql in tabelas.items():
        cursor.execute(sql)
        print(f"🗃️ Tabela '{nome}' pronta.")

# =========================
# Função genérica de importação
# =========================
def importar_json(arquivo_json, tabela):
    conn = conectar()
    if not conn:
        return

    cursor = conn.cursor()
    criar_tabelas(cursor)

    with open(arquivo_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    registros = 0
    for item in data.get("results", []):
        if not item.get("unique_id"):
            continue

        if tabela == "loadbalancers":
            cursor.execute("""
                INSERT INTO loadbalancers (unique_id, id, display_name, description, connectivity_path, size, resource_type, create_user, last_modified_user)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    display_name=VALUES(display_name),
                    description=VALUES(description),
                    size=VALUES(size),
                    last_modified_user=VALUES(last_modified_user)
            """, (
                item.get("unique_id"),
                item.get("id"),
                item.get("display_name"),
                item.get("description"),
                item.get("connectivity_path"),
                item.get("size"),
                item.get("resource_type"),
                item.get("_create_user"),
                item.get("_last_modified_user")
                item.get("tags"),
                item.get("resource_type"),
                item.get("default_pool_member_ports"),
                item.get("access_log_enabled"),
                item.get("enabled")
            ))

        elif tabela == "virtual_servers":
            cursor.execute("""
                INSERT INTO virtual_servers (unique_id, id, display_name, ip_address, ports, lb_service_path, pool_path, description, create_user, last_modified_user)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    display_name=VALUES(display_name),
                    ip_address=VALUES(ip_address),
                    lb_service_path=VALUES(lb_service_path)
            """, (
                item.get("unique_id"),
                item.get("id"),
                item.get("display_name"),
                item.get("ip_address"),
                ",".join(item.get("ports", [])) if isinstance(item.get("ports"), list) else None,
                item.get("lb_service_path"),
                item.get("pool_path"),
                item.get("description"),
                item.get("_create_user"),
                item.get("_last_modified_user")
            ))

        elif tabela == "pools":
            cursor.execute("""
                INSERT INTO pools (unique_id, id, display_name, description, algorithm, monitor_path, member_count, create_user, last_modified_user)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    display_name=VALUES(display_name),
                    algorithm=VALUES(algorithm),
                    member_count=VALUES(member_count)
            """, (
                item.get("unique_id"),
                item.get("id"),
                item.get("display_name"),
                item.get("description"),
                item.get("algorithm"),
                item.get("monitor_path"),
                len(item.get("members", [])) if "members" in item else 0,
                item.get("_create_user"),
                item.get("_last_modified_user")
            ))

        registros += 1

    conn.commit()
    cursor.close()
    conn.close()
    print(f"📦 {registros} registros importados/atualizados na tabela '{tabela}'.\n")

# =========================
# Execução principal
# =========================
if __name__ == "__main__":
    importar_json("lb-services.json", "loadbalancers")
    importar_json("lb-virtual-servers.json", "virtual_servers")
    importar_json("lb-pools.json", "pools")

