import os
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template_string, request

# Variáveis de configuração, com valores padrão e possibilidade de sobrescrita via variáveis de ambiente para flexibilidade. O diretório de upload é configurável, assim como o caminho do script de importação e o interpretador Python a ser usado. 
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_ROOT = Path(os.environ.get("UPLOAD_ROOT", BASE_DIR / "uploads"))
SCRIPT_PATH = Path(
    os.environ.get(
        "IMPORT_SCRIPT",
        BASE_DIR / "importa_vhost_vinfo_vnetwork_vdisk.py",
    )
)

PYTHON_BIN = os.environ.get("PYTHON_BIN", sys.executable) # caminho para o interpretador Python (pode ser configurado via variável de ambiente, padrão é o mesmo do ambiente atual)
ALLOWED_EXT = {".zip"} # conjunto de extensões permitidas para upload (apenas .zip neste caso)

app = Flask(__name__) # instância do aplicativo Flask, que é a base para criar as rotas e lidar com as requisições HTTP. O nome do módulo é passado para o Flask para ajudar na localização de recursos e templates, embora neste caso estou utilizando usando render_template_string para manter tudo em um único arquivo. Para facilitar deploy em Container, o debug está desativado por padrão, mas pode ser ativado facilmente alterando a variável de ambiente ou o código diretamente. O aplicativo é configurado para rodar na porta 8000 e aceitar conexões de qualquer endereço (0.0.0.0).

# Página HTML para upload de arquivos e exibição de mensagens! Utiliza render_template_string para manter tudo em um único arquivo, mas pode ser facilmente adaptada para usar templates separados se necessário.
PAGE = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <title>Importador RVTools</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 760px; margin: 40px auto; }
    form { display: grid; gap: 12px; margin-bottom: 20px; }
    input[type=file] { padding: 8px; }
    button { padding: 10px 16px; cursor: pointer; }
    pre { background: #f5f5f5; padding: 12px; border-radius: 6px; white-space: pre-wrap; }
    label { display: flex; align-items: center; gap: 8px; }
  </style>
</head>
<body>
  <h1>Importador RVTools v1</h1>
  <form method="post" enctype="multipart/form-data">
    <div>
    <label>Arquivo (.zip importado do RVTools)</label>
    <input type="file" name="file" accept=".zip" required />
    </div>
    <label>
      <input type="checkbox" name="run_import" checked /> Executar importação após upload
    </label>
    <button type="submit">Enviar</button>
  </form>
  {% if message %}<pre>{{ message }}</pre>{% endif %}
</body>
</html>
"""


def ensure_upload_root() -> None: # função para garantir que o diretório de upload exista, criando-o se necessário
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True) # mkdir com parents=True permite criar toda a hierarquia de diretórios se não existir, exist_ok=True evita erro se o diretório já existir


def save_and_extract(file_storage) -> Path: # está esperando um objeto FileStorage do Flask
    ensure_upload_root() # garante que o diretório de upload exista
    suffix = Path(file_storage.filename).suffix.lower() # extrai a extensão do arquivo e converte para minúscula
    if suffix not in ALLOWED_EXT: # verifica se a extensão é permitida
        raise ValueError("Extensão NÃO PERMITIDA! Envie um único arquivo .zip.") # lança um erro se a extensão não for permitida
    
    batch_dir = UPLOAD_ROOT / f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}" # cria um nome de diretório único baseado na data e hora atual para evitar conflitos
    batch_dir.mkdir(parents=True, exist_ok=True) # cria o diretório para extrair os arquivos, garantindo que a hierarquia seja criada se necessário e evitando erros se o diretório já existir

    with tempfile.TemporaryDirectory() as tmpdir: # usa um diretório temporário para salvar o arquivo zip enviado, garantindo que ele seja limpo automaticamente após a extração
        tmp_path = Path(tmpdir) / file_storage.filename # caminho completo para o arquivo zip temporário
        file_storage.save(tmp_path) # salva o arquivo enviado no caminho temporário

        with zipfile.ZipFile(tmp_path, "r") as zf: # abre o arquivo zip para leitura usando a biblioteca zipfile, garantindo que ele seja fechado automaticamente após a operação
            zf.extractall(batch_dir) # extrai todo o conteúdo do arquivo zip para o diretório de destino criado anteriormente, preservando a estrutura de diretórios interna do zip

    return batch_dir # retorna o caminho do diretório onde os arquivos foram extraídos, que será usado posteriormente para executar o script de importação nesse diretório específico


def run_import_script(working_dir: Path) -> tuple[int, str]: # função para executar o script de importação no diretório especificado
    if not SCRIPT_PATH.exists(): # verifica se o script de importação existe antes de tentar executá-lo, retornando um código de erro e mensagem apropriada se não for encontrado
        return 1, f"Script não encontrado em {SCRIPT_PATH}" # retorna código de erro 1 e mensagem indicando que o script não foi encontrado

    cmd = [PYTHON_BIN, str(SCRIPT_PATH)] # comando para executar o script de importação usando o interpretador Python especificado, convertendo o caminho do script para string para garantir compatibilidade com subprocess
    result = subprocess.run( 
        cmd,
        cwd=working_dir,
        capture_output=True,
        text=True,
        env={**os.environ, "UPLOAD_ROOT": str(UPLOAD_ROOT)}, # passa o diretório de upload como variável de ambiente para o script
    )
    output = result.stdout + (result.stderr or "")
    return result.returncode, output


@app.route("/", methods=["GET", "POST"]) # rota principal do aplicativo, que aceita tanto requisições GET para exibir a página de upload quanto POST para processar o arquivo enviado e executar o script de importação
def index(): 
    message = ""
    if request.method == "POST": # Metodo POST para processar o upload do arquivo e executar o script de importação
        file = request.files.get("file")
        if not file:
            message = "Nenhum arquivo enviado."
        else:
            try:
                target_dir = save_and_extract(file)
                should_run = request.form.get("run_import") is not None
                if should_run:
                    code, output = run_import_script(target_dir)
                    prefix = "Importação concluída" if code == 0 else "Falha na importação"
                    message = f"{prefix} (code {code})\n\n{output}"
                else:
                    message = f"Upload concluído em {target_dir}. Execução não disparada."
            except Exception as exc:  # noqa: BLE001
                message = f"Erro: {exc}"
    return render_template_string(PAGE, message=message)




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)