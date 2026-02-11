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
RVTOOLS_ROOT = BASE_DIR / "RVTOOLS" # Pasta central solicitada - onde os arquivos serão organizados por data
ALLOWED_EXT = {".zip"} # Extensão permitida, somente arquivos zipados dos relatórios do RVTools
IMPORT_SCRIPT = BASE_DIR / "importa_vhost_vinfo_vnetwork_vdisk.py" # Script de importação que será chamado em background
PYTHON_BIN = sys.executable # Caminho do interpretador Python atual (garante compatibilidade com ambientes virtuais)

app = Flask(__name__)

# HTML da página, usando render_template_string para manter tudo em um arquivo só. 
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
    <h2>Importador RVTools</h2>
    <p>Upload de relatórios vCenter para importação em banco de dados.</p>
    
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
      * O processamento do banco de dados ocorre em background. Print no Terminal do VS Code/WSL confirmará o sucesso ou falha da importação, além do tempo gasto após o término.
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
    dia, mes, _, ano_curto = match.groups() # Reorganiza para formato YYMMDD - o ano vem por último no nome do arquivo, mas quero ele no início da pasta
    return f"{ano_curto}{mes}{dia}" # Formato final da pasta: RVTOOLS/YYMMDD

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
            print("[STATUS]: Sucesso! Dados inseridos no MySQL.")
            # ver os print's do script de importação para detalhes do que foi processado
            print(f"[DETALHES]: {result.stdout}")

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
                
                # Verifica se já existe algum arquivo processado nessa pasta
                if target_dir.exists() and any("_PROCESSADO" in f.name for f in target_dir.iterdir()):
                    message = f"AVISO: A data {folder_name} já foi processada anteriormente. Limpe a pasta manualmente se desejar reimportar."
                    return render_template_string(PAGE, message=message)

                # Se passou pela verificação, cria a pasta (mesmo que já exista, para garantir a estrutura), não altera o conteúdo se já tiver algo lá
                target_dir.mkdir(parents=True, exist_ok=True)
                
                # Verifica se já existe algum arquivo processado nessa pasta
                if target_dir.exists() and any("_PROCESSADO" in f.name for f in target_dir.iterdir()):
                    message = f"AVISO: A data {folder_name} já foi processada anteriormente. Limpe a pasta manualmente se desejar reimportar."
                    return render_template_string(PAGE, message=message)

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
                           f"O script de importação está sendo executado em background.\n"
                           f"Print no Terminal do VS Code/WSL confirmará o sucesso ou falha da importação, além do tempo gasto após o término.")

            except Exception as e:
                message = f"ERRO ao processar arquivo: {str(e)}"
                
    return render_template_string(PAGE, message=message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
