import subprocess
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from flask import Flask, render_template_string, request

# Configurações de diretório
BASE_DIR = Path(__file__).resolve().parent
# Pasta central solicitada
RVTOOLS_ROOT = BASE_DIR / "RVTOOLS"
ALLOWED_EXT = {".zip"}

# Certifique-se que o nome do arquivo abaixo é o mesmo do seu script de banco
IMPORT_SCRIPT = BASE_DIR / "importa_vhost_vinfo_vnetwork_vdisk.py"
PYTHON_BIN = sys.executable

app = Flask(__name__)

PAGE = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>Upload RVTools - Organizado</title>
  <style>
    body { font-family: 'Segoe UI', sans-serif; max-width: 700px; margin: 40px auto; background: #f4f7f6; }
    .card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    h2 { color: #2c3e50; margin-top: 0; }
    form { display: flex; flex-direction: column; gap: 15px; }
    input[type=file] { border: 1px solid #ddd; padding: 10px; border-radius: 5px; }
    button { background: #27ae60; color: white; border: none; padding: 12px; cursor: pointer; border-radius: 5px; font-weight: bold; }
    button:hover { background: #219150; }
    pre { background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap; }
  </style>
</head>
<body>
  <div class="card">
    <h2>📁 Importador RVTools</h2>
    <p>O sistema extrairá a data do nome do arquivo (ex: 08012026) e criará a pasta <b>AAAA-MM-DD</b> dentro de <code>RVTOOLS/</code>.</p>
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="file" accept=".zip" required />
      <button type="submit">Processar Relatórios</button>
    </form>
  </div>
  
  {% if message %}
    <h3>Log de Operação:</h3>
    <pre>{{ message }}</pre>
  {% endif %}
</body>
</html>
"""

def extract_date_from_filename(filename: str) -> str:
    """
    Busca 8 dígitos seguidos no nome do arquivo e transforma em YYMMDD
    Exemplo: Relatorios_vCenters_08012026.zip -> 260108
    """
    #match = re.search(r'(\d{2})(\d{2})(\d{4})', filename) # busca por 8 dígitos seguidos (DDMMYYYY)
    match = re.search(r'(\d{2})(\d{2})(\d{2})(\d{2})', filename) # busca por 6 dígitos seguidos (DDMMYY) - o terceiro \d{2} ignora os 4 dígitos do ano, pegando apenas os 2 últimos para formar o nome da pasta. Ex: 10012026 -> 2026-01-10
    if not match:
        # Fallback caso o nome venha fora do padrão: usa o dia de hoje. Tirar futuramente, pois o ideal é que o nome do arquivo sempre venha com a data para organizar as pastas corretamente.
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d_fallback')
    
#    dia, mes, ano = match.groups()
#    return f"{ano}-{mes}-{dia}"
    dia, mes, ano_milênio, ano_curto = match.groups()
    return f"{ano_curto}{mes}{dia}" # Retorna no formato YYMMDD para criar a pasta. Exemplo: 10012026 -> 260110 (ano curto + mês + dia)

def save_and_extract(file_storage) -> tuple[Path, list[str]]: # -> (Path da pasta destino, lista de arquivos extraídos):
    """Salva o arquivo enviado e extrai seu conteúdo na pasta correta."""
    RVTOOLS_ROOT.mkdir(parents=True, exist_ok=True)
    
    # Validação básica de extensão - tipo de arquivo
    filename = file_storage.filename
    if not filename.lower().endswith('.zip'):
        raise ValueError("Apenas arquivos .zip são permitidos.")

    # 1. Extrair data para o nome da pasta
    folder_name = extract_date_from_filename(filename)
    target_dir = RVTOOLS_ROOT / folder_name # Pasta destino: RVTOOLS/YYMMDD. Se o nome do arquivo não tiver a data, a pasta será criada com a data atual e sufixo _fallback, ex: RVTOOLS/2024-06-17_fallback. O ideal é que o nome do arquivo sempre venha com a data para organizar as pastas corretamente.
    
    # 2. Lógica para evitar duplicidade ou sobrescrever
    # Caso queira evitar a subscrição, pode-se adicionar um sufixo _v2, _v3...
    # Por padrão aqui, ele extrairá por cima se a data for a mesma.
    target_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / filename
        file_storage.save(tmp_path)

        with zipfile.ZipFile(tmp_path, "r") as zf:
            file_list = zf.namelist()
            zf.extractall(target_dir)

    return target_dir, file_list



def run_import_process(target_folder: Path):
    """Executa o script de banco de dados no diretório específico."""
    if not IMPORT_SCRIPT.exists():
        return f"ERRO: Script de importação não encontrado em {IMPORT_SCRIPT}"
    
    env = os.environ.copy()
    env['PLAN_DIR'] = str(target_folder)
    
    try:
        result = subprocess.run(
            [PYTHON_BIN, str(IMPORT_SCRIPT)],
            capture_output=True,
            text=True,
            env=env
        )
        return result.stdout + (result.stderr or "")
    except Exception as e:
        return f"Falha na execução do subprocesso: {str(e)}"

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename:
            try:
                # 1. Definir pasta destino
                folder_name = extract_date_from_filename(file.filename)
                target_dir = RVTOOLS_ROOT / folder_name
                target_dir.mkdir(parents=True, exist_ok=True)

                # 2. Salvar ZIP temporário e extrair
                with tempfile.TemporaryDirectory() as tmpdir:
                    temp_zip = Path(tmpdir) / file.filename
                    file.save(temp_zip)
                    
                    with zipfile.ZipFile(temp_zip, "r") as zf:
                        zf.extractall(target_dir)

                # 3. Chamar script de banco de dados
                db_logs = run_import_process(target_dir)
                message = f"Pasta Criada: RVTOOLS/{folder_name}\n\n--- LOGS DO BANCO ---\n{db_logs}"

            except Exception as e:
                message = f"ERRO NO SERVIDOR: {str(e)}"
                
    return render_template_string(PAGE, message=message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)