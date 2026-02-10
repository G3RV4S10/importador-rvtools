import subprocess
import os
import re
import sys
import tempfile
import zipfile
import threading
import time # Para calcular o tempo de execução
from pathlib import Path
from flask import Flask, render_template_string, request

# Configurações de diretório
BASE_DIR = Path(__file__).resolve().parent
RVTOOLS_ROOT = BASE_DIR / "RVTOOLS"
IMPORT_SCRIPT = BASE_DIR / "importa_vhost_vinfo_vnetwork_vdisk.py"
PYTHON_BIN = sys.executable

app = Flask(__name__)

# HTML com uma estética levemente mais profissional
PAGE = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>RVTools Dataprev - Background Importer</title>
  <style>
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 700px; margin: 40px auto; background: #eef2f3; }
    .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.1); }
    h2 { color: #2c3e50; border-left: 5px solid #27ae60; padding-left: 15px; }
    .status-msg { background: #d1ecf1; color: #0c5460; padding: 15px; border-radius: 6px; border: 1px solid #bee5eb; margin-top: 20px; }
    .footer-info { font-size: 12px; color: #7f8c8d; margin-top: 15px; }
    button { background: #2ecc71; color: white; border: none; padding: 12px 24px; cursor: pointer; border-radius: 6px; font-weight: bold; width: 100%; }
    button:hover { background: #27ae60; }
  </style>
</head>
<body>
  <div class="card">
    <h2>🚀 Importador RVTools</h2>
    <p>Upload de relatórios vCenter para processamento em segundo plano.</p>
    
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="file" accept=".zip" required style="margin-bottom: 20px; width: 100%;">
      <button type="submit">Iniciar Upload e Importação</button>
    </form>

    {% if message %}
      <div class="status-msg">
        {{ message | replace('\n', '<br>') | safe }}
      </div>
    {% endif %}
    
    <div class="footer-info">
      * O processamento do banco de dados ocorre em background. Acompanhe o terminal do VS Code/WSL para ver o progresso real.
    </div>
  </div>
</body>
</html>
"""

def extract_date_from_filename(filename: str) -> str:
    match = re.search(r'(\d{2})(\d{2})(\d{2})(\d{2})', filename)
    if not match:
        from datetime import datetime
        return datetime.now().strftime('%y%m%d')
    dia, mes, _, ano_curto = match.groups()
    return f"{ano_curto}{mes}{dia}"

def run_import_process(target_folder: Path):
    """Executa a importação e loga o resultado final no console."""
    start_time = time.time()
    folder_name = target_folder.name
    
    print(f"\n{'='*50}")
    print(f"[BACKGROUND START] Iniciando processamento da pasta: {folder_name}")
    print(f"{'='*50}")

    env = os.environ.copy()
    env['PLAN_DIR'] = str(target_folder)
    
    try:
        result = subprocess.run(
            [PYTHON_BIN, str(IMPORT_SCRIPT)],
            capture_output=True,
            text=True,
            env=env
        )
        
        duration = time.time() - start_time
        
        # Log de Sucesso no Terminal
        print(f"\n{'*'*50}")
        print(f"[BACKGROUND FINISHED] Pasta: {folder_name}")
        print(f"[TEMPO TOTAL]: {duration:.2f} segundos")
        
        if result.returncode == 0:
            print(f"[STATUS]: Sucesso! Dados inseridos no MySQL.")
        else:
            print(f"[STATUS]: O script retornou um erro (Código {result.returncode})")
            print(f"[ERRO]: {result.stderr}")
        print(f"{'*'*50}\n")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] Falha na thread de importação: {str(e)}")

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        file = request.files.get("file")
        if file and file.filename:
            try:
                folder_name = extract_date_from_filename(file.filename)
                target_dir = RVTOOLS_ROOT / folder_name
                target_dir.mkdir(parents=True, exist_ok=True)

                # Extração rápida
                with tempfile.TemporaryDirectory() as tmpdir:
                    temp_zip = Path(tmpdir) / file.filename
                    file.save(temp_zip)
                    with zipfile.ZipFile(temp_zip, "r") as zf:
                        zf.extractall(target_dir)

                # Dispara a Thread e avisa o usuário
                thread = threading.Thread(target=run_import_process, args=(target_dir,))
                thread.start()

                message = (f"Arquivo recebido!\n"
                           f"Destino: RVTOOLS/{folder_name}\n"
                           f"O banco de dados está sendo atualizado agora.\n"
                           f"Fique de olho no terminal para a confirmação final.")

            except Exception as e:
                message = f"ERRO ao processar arquivo: {str(e)}"
                
    return render_template_string(PAGE, message=message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
