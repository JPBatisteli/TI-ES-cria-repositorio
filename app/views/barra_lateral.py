import streamlit as st

from app import config


def configurar_barra_lateral() -> str:
    """
    Monta a barra lateral com as configurações de acesso ao GitHub.

    A barra lateral é comum a todas as abas da aplicação, por isso é montada uma
    única vez e o token é repassado às visões que dele necessitam.

    Returns:
        str: Token do GitHub informado pelo professor ou carregado do arquivo .env.
    """
    with st.sidebar:
        st.header("Configurações")

        token_padrao = config.GITHUB_TOKEN or ""
        token = st.text_input(
            "Token do GitHub",
            value=token_padrao,
            type="password",
            help="Token pessoal com escopo 'repo' e permissão para criar repositórios na organização."
        )

        if token_padrao:
            st.caption("Token carregado do arquivo `.env`.")
        else:
            st.caption("Nenhum token encontrado no arquivo `.env`. Informe o seu token acima.")

        st.divider()
        st.subheader("Padrão de nomenclatura")
        st.code(
            "<campus>-es-<ano>-<semestre>-<ti>-<codigo>-<nome>",
            language="text"
        )
        st.caption("Exemplo: `pmg-es-2025-1-ti2-3687100-brecho-re-use`")

    return token
