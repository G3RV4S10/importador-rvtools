# Pequeno Guia com comandos caso eu venha a esquecer;

Este guia documenta o processo de **conteinerização** da aplicação utilizando **Debian 12**, **Python 3.11** e **Docker**, com foco em padronização, reprodutibilidade;

---

##  1. Estrutura de Arquivos

Antes de iniciar o deploy, valide se o diretório de trabalho contém a seguinte estrutura:

- `app-v3.py` — Script Flask (API)
- `importa_vhost_vinfo_vnetwork_vdisk.py` — Script de persistência em banco de dados
- `requirements.txt` — Dependências Python  
  - `flask`  
  - `pandas`  
  - `openpyxl`  
  - `mysql-connector-python`
- `Dockerfile`
- `docker-compose.yml`
- Pasta `./files/`
  - `sources.list.bookworm`
  - `.bashrc`
  - outros arquivos auxiliares

Essa organização p garantir clareza e facilitar manutenções futuras.

---

## 2. Dockerfile

O `Dockerfile` abaixo isola a aplicação em um ambiente controlado, garantindo:

- Uso de **Debian 12 (bookworm-slim)**
- **Python 3.11** com ambiente virtual dedicado
- Configuração correta de **timezone** para consistência de logs
- Compatibilidade com `docker logs -f`

```dockerfile
FROM debian:bookworm-slim

# Configurações de repositório e pacotes de sistema
COPY ./files/sources.list.bookworm /etc/apt/sources.list

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    ca-certificates \
    tzdata \
    nano \
    locales \
    vim && \
    # Ajuste de Timezone para log correto
    ln -fs /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Ambiente Virtual para evitar conflitos no Debian
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalação das dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Cópia dos scripts da aplicação
COPY . .

# Log em tempo real (essencial p docker logs -f)
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python3", "app-v3.py"]
````

No terminal apos builder de imagem;
Execução manual com docker run:
```bash
docker run -d \
--name rvtools-importer \
-p 8000:8000 \
-v $(pwd)/RVTOOLS:/app/RVTOOLS \
--restart unless-stopped \
<imagem-nome>

docker run -d: O -d significa detached mode. Ele inicia o container em segundo plano. Sem isso, caso eu venha fechar o terminal ou desse Ctrl+C, o importador pararia de funcionar.
--name <container-nome>: Atribui um nome ao container. Em vez do Docker gerar um nome aleatório (como confuso_sobrinho), utilizar nome para ver logs ou parar o serviço..
-p 8000:8000: Faz o mapeamento de portas (HOST:CONTAINER). Ele pega a porta 8000(padrãoqueoflaskabri) do Debian do container e a expõe na porta 8000 do servidor físico ou vm. 
-v $(pwd)/RVTOOLS:/app/RVTOOLS: Este é o Volume. O $(pwd) pega o diretório atual no linux. Ele "espelha" a pasta local com a pasta dentro do container.
--restart unless-stopped: uma "política" de resiliência. Se o servidor venha reiniciar por falta de energia/manutenção ou um imprevisto no ambiente, o Docker subirá o container automaticamente assim que o sistema voltar, a menos que eu o tenha parado manualmente antes.
<imagem-nome>: É o nome da imagem que eu dei um builder e que servirá de base para rodar a "aplicação".
```
OBS: espelhamento será temporario até eu setar um volume persistente;

---

## 3. Gerenciamento com Docker Compose
O Compose p facilitar a subida do serviço sem precisar digitar todos os parâmetros do docker run a dedo(manualmente).

Criar arquivo docker-compose.yml:
```YAML
version: '3.8'
services:
  rvtools-importer:
    build: .
    image: debian-rvtools:v3
    container_name: rvtools-importer
    ports:
      - "8000:8000"
    volumes:
      - ./RVTOOLS:/app/RVTOOLS
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
```

---

## 4. Construir e Subir (via Docker Compose)

```bash
#Constrói a imagem e inicia o container em background
docker compose up -d --build
```
---

## COMANDOS P GERENCIAMENTO:
| Ação                   | Comandos                              |
|------------------------|---------------------------------------|
| Ver logs em tempo real | docker logs -f rvtools-importer       |
| Parar o serviço        | docker stop rvtools-importer          |
| Iniciar o serviço      | docker start rvtools-importer         |
| Entrar no container    | docker exec -it rvtools-importer bash |
| Remover o container    | docker rm -f rvtools-importer         |




