from pathlib import Path

from dotenv import load_dotenv
import os

# Caminho do arquivo .env na raiz do projeto. Informá-lo explicitamente garante que
# as variáveis sejam carregadas mesmo quando a aplicação é executada a partir de
# outro diretório.
CAMINHO_ARQUIVO_ENV = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(dotenv_path=CAMINHO_ARQUIVO_ENV) # Carrega as variáveis do arquivo .env

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
