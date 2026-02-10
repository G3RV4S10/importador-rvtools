# importador-rvtools
Projeto em Python para automatizar a extração, transformação e carga (ETL) de dados de inventário do VMware vCenter. O script lê relatórios em formato Excel (.xlsx) gerados pelo RVTools, processa informações de hosts e VMs, e as armazena em um banco de dados MySQL para análise e criação de histórico.


# Pequeno passo a passo de como utilizar

## 1. Preparar o ambiente
- Instalar dependências:

``` bash
pip install -r requirements.txt
```

Ajuste credenciais em variáveis de ambiente (DB_USER, DB_PASS, DB_HOST, DB_NAME, DB_PORT, PLAN_DIR) ou edite o dicionário DB_CONFIG em importa_vhost_vinfo_vnetwork_vdisk.py.

Crie o schema MySQL executando schema_vhost_vinfo_vnetwork_vdisk.sql.

Preparar os arquivos de entrada

Coloque as planilhas .xlsx em PLAN_DIR (padrão: RVTOOLS), incluindo subpastas se quiser.
Nome dos arquivos deve conter a data em ddmmyyyy (ex.: rvtools_25082024.xlsx). Caso contrário, extrair_data_do_arquivo ignorará o arquivo.
As abas necessárias são: vHost, vInfo, vNetwork, vDisk, com colunas mapeadas em VHOST_COLS, VINFO_COLS, VNETWORK_COLS, VDISK_COLS.
Executar a importação

Rodarr:
O script varre PLAN_DIR recursivamente, insere em hosts, vms, networks, vdisks e renomeia o arquivo para _PROCESSADO.xlsx ao concluir.
Validar resultado
Verifique logs no console (avisos sobre colunas/abas ausentes).
Confirme dados no MySQL (tabelas hosts, vms, networks, vdisks).
Para reprocessar, remova o sufixo _PROCESSADO ou use remove_processado_de_xlss.py.
Passo a passo para usar o website (interface web provisória) – arquivo app.py

Ambiente
Instale dependências (mesmo requirements.txt).
Opcional: defina variáveis UPLOAD_ROOT (onde extrações serão salvas), IMPORT_SCRIPT (caminho do script de importação, padrão é o mesmo acima) e PYTHON_BIN (interpretador).
Subir o servidor

Execute:
Acesse http://localhost:8000/.
Upload & importação

Envie um .zip contendo os .xlsx com data no nome (padrão ddmmyyyy). O backend extrai no diretório uploads/batch_YYYYMMDD_HHMMSS.
A opção “Executar importação após upload” vem marcada; se mantida, chamará o script definido em IMPORT_SCRIPT dentro da pasta extraída.
Acompanhar logs

O resultado (stdout/stderr) do script aparece na página após o envio.
Mesmo incompleto, já permite testar o fluxo de upload + execução; para casos fora do padrão de nome/data, o script não importará e registrará aviso no log.




