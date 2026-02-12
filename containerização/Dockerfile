FROM debian:bookworm-slim

COPY ./files/sources.list.bookworm /etc/apt/sources.list

# Instalando pacotes do repositorio oficial do Debian
# Padronizando versão do pyton para a v 3.11. Objetivo é implementar posteriormente a biblioteca gunicorn. Utilizado para servir a aplição flask
RUN apt-get update -qq && \
apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-distutils \
    python3-pip \
    ca-certificates \
    tzdata \
    vim \
    bash-completion \
    iputils-ping \
    locales \
    nano \
    dialog && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

#Copia cores setado no meu ambiente para o terminal ficar frofro(beauty)
COPY ./files/cores.defs /etc
COPY ./files/.bashrc /root
COPY ./files/timezone /etc

# Acertando o TIMEZONE
RUN ln -fs /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime
RUN dpkg-reconfigure -f noninteractive tzdata

# Limpando os pacotes baixados
RUN apt-get autoremove
RUN apt-get autoclean

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Cria um ambiente virtual para evitar conflitos com o Python do sistema
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copia e instala dependências/bibliotecas do scritp do requirements local. Pegar no github caso eu me esqueça
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#Copia arquivos do diretorio atual p container
#Colocar no diretorio atual o app-v3.py e importa_vhost_vinfo_vnetwork_vdisk.py
COPY . .

# Garante que logs apareçam na console do Docker
# docker container logs ou docker logs -f <nomecontainer>
ENV PYTHONUNBUFFERED=1

#Expoe a porta 8000, é a utilizada pelo flask ao rodar o app.py
EXPOSE 8000

# Executa diretamente com o interpretador do venv
CMD ["python3", "app-v3.py"]

# Para o gunicorn
#CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:8000", "--timeout", "120", "app-v3:app"]
