import subprocess
import os
import re
import sys
import tempfile
import zipfile
import threading
import time
from pathlib import Path
from flask import Flask, render_template_string, request

# Configurações
BASE_DIR = Path(__file__).resolve().parent
RVTOOLS_ROOT = BASE_DIR / "RVTOOLS"
IMPORT_SCRIPT = BASE_DIR / "importa_vhost_vinfo_vnetwork_vdisk.py"
PYTHON_BIN = sys.executable

app = Flask(__name__)

# LOCK GLOBAL: Impede que duas threads de importação rodem ao mesmo tempo
import_lock = threading.Lock()

PAGE = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>RVTools Dataprev - Importer</title>
  <style>
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 700px; margin: 40px auto; background: #eef2f3; }
    .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.1); }
    h2 { color: #2c3e50; border-left: 5px solid #27ae60; padding-left: 15px; }
    .status-msg { background: #d1ecf1; color: #0c5460; padding: 15px; border-radius: 6px; border: 1px solid #bee5eb; margin-top: 20px; }
    button { background: #2ecc71; color: white; border: none; padding: 12px 24px; cursor: pointer; border-radius: 6px; font-weight: bold; width: 100%; }
    button:hover { background: #27ae60; }
    button:disabled { background: #95a5a6; cursor: not-allowed; }
  </style>
</head>
<body>
  <div class="card">
    <h2>Importador RVTools</h2>
    <p>Upload de relatórios vCenter para importação em banco de dados.</p>
    
    <form method="post" enctype="multipart/form-data" onsubmit="this.btn.disabled=true; this.btn.innerText='Processando...';">
      <input type="file" name="file" accept=".zip" required style="margin-bottom: 20px; width: 100%;">
      <button type="submit" name="btn">Iniciar Upload e Importação</button>
    </form>

    {% if message %}
      <div class="status-msg">{{ message | replace('\n', '<br>') | safe }}</div>
    {% endif %}
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
    # Tenta adquirir o lock. Se já tiver algo rodando, ele espera ou pode tratar.
    # usar o lock para garantir que uma importação não atropele a outra.
    with import_lock:
        start_time = time.time()
        print(f"\n{'='*50}\n[INÍCIO] Processando: {target_folder.name}\n{'='*50}")

        env = os.environ.copy()
        env['PLAN_DIR'] = str(target_folder)
        
        try:
            # "-u" força o python a não usar buffer na saída (tempo real total)
            process = subprocess.Popen(
                [PYTHON_BIN, "-u", str(IMPORT_SCRIPT)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                bufsize=1
            )

            if process.stdout:
                for line in process.stdout:
                    print(f"  > {line.strip()}", flush=True) #Imprime cada linha do log do processo filho(importa_vhost_vinfo_vnetwork_vdisk.py) em tempo REALL

            process.wait()
            duration = time.time() - start_time
            print(f"\n{'*'*50}\n[FIM] Tempo: {duration:.2f}s | Status: {process.returncode}\n{'*'*50}")

        except Exception as e:
            print(f"\n[ERRO CRÍTICO]: {str(e)}")

@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        # Verificação rápida: Se o Lock está ocupado, não permite iniciar outra importação
        if import_lock.locked():
            return render_template_string(PAGE, message="ERRO: Já existe uma importação em andamento. Aguarde o término.")

        file = request.files.get("file")
        if file and file.filename:
            try:
                folder_name = extract_date_from_filename(file.filename)
                target_dir = RVTOOLS_ROOT / folder_name

                # Validação de arquivo já processado (Sua Solução 2)
                if target_dir.exists() and any("_PROCESSADO" in f.name for f in target_dir.iterdir()):
                    return render_template_string(PAGE, message=f"Aviso: A data {folder_name} já foi processada.")

                target_dir.mkdir(parents=True, exist_ok=True)

                with tempfile.TemporaryDirectory() as tmpdir:
                    temp_zip = Path(tmpdir) / file.filename
                    file.save(temp_zip)
                    with zipfile.ZipFile(temp_zip, "r") as zf:
                        zf.extractall(target_dir)

                # Dispara a Thread
                threading.Thread(target=run_import_process, args=(target_dir,)).start()

                message = f"Arquivo recebido! Processando data {folder_name}.\nAcompanhe os logs no terminal."

            except Exception as e:
                message = f"Erro: {str(e)}"
                
    return render_template_string(PAGE, message=message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)