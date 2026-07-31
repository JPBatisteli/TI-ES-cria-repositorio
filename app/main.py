import sys
from pathlib import Path

# O comando `streamlit run` adiciona ao sys.path apenas a pasta do script executado
# (app/). A linha abaixo acrescenta a raiz do projeto, permitindo que os imports no
# formato `app.<pacote>` funcionem a partir de qualquer diretório de execução.
RAIZ_DO_PROJETO = Path(__file__).resolve().parent.parent
if str(RAIZ_DO_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_DO_PROJETO))

import streamlit as st

from app.views.barra_lateral import configurar_barra_lateral
from app.views.criacao_lote_view import CriacaoLoteView
from app.views.criacao_repositorio_view import CriacaoRepositorioView

criacao_repositorio_view = CriacaoRepositorioView()
criacao_lote_view = CriacaoLoteView()

if __name__ == '__main__':
    st.set_page_config(page_title="Criador de Repositórios de TI", layout="wide")

    st.title("📦 Criador de Repositórios de TI")

    # A barra lateral é comum às abas, por isso é montada antes delas.
    token = configurar_barra_lateral()

    aba_individual, aba_lote = st.tabs(["Repositório individual", "Criação em lote"])

    with aba_individual:
        criacao_repositorio_view.render(token)

    with aba_lote:
        criacao_lote_view.render(token)
