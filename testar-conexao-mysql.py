import mysql.connector
from mysql.connector import Error

# =========================
# Configuração do Banco
# =========================
DB_CONFIG = {
    'user': 'root',
    'password': 'Lab2024!',
    'host': '192.168.255.107', 
    'database': 'testeteste',
    'port': 3307
}

# =========================
# Teste de Conexão
# =========================
try:
    print("Tentando conectar ao banco de dados...")
    conn = mysql.connector.connect(**DB_CONFIG)

    if conn.is_connected():
        print("✅ Conexão bem-sucedida ao banco MySQL!")
        print(f"Banco de dados conectado: {DB_CONFIG['database']}")
        print(f"Host: {DB_CONFIG['host']} | Usuário: {DB_CONFIG['user']}")

except Error as e:
    print(f"❌ Erro ao conectar: {e}")

finally:
    if 'conn' in locals() and conn.is_connected():
        conn.close()
        print("🔒 Conexão encerrada com segurança.")