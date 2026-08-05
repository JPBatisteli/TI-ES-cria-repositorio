# A aplicação usa sintaxe de anotações introduzida no Python 3.10 (`dict | None`),
# por isso a imagem fixa a versão 3.11, a mesma do ambiente de desenvolvimento.
FROM python:3.11-slim

# Evita arquivos .pyc no contêiner e garante que os logs apareçam sem atraso.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# As dependências são instaladas antes do código para que o cache de camadas só
# seja invalidado quando o requirements.txt mudar.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# A pasta docs acompanha a imagem porque a aba de criação em lote lê dela o
# arquivo de exemplo oferecido no botão "Baixar modelo comentado".
COPY app/ ./app/
COPY docs/ ./docs/

# A aplicação não precisa de privilégios de root para ser executada.
RUN useradd --create-home --uid 1000 streamlit \
    && chown -R streamlit:streamlit /app
USER streamlit

EXPOSE 8501

# O endpoint /_stcore/health é o verificador de saúde do próprio Streamlit.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

# O token não é embutido na imagem: deve ser informado em tempo de execução, por
# variável de ambiente ou pela barra lateral da aplicação.
CMD ["streamlit", "run", "app/main.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
