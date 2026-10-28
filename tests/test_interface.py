"""
Testes que exercitam a interface pelo AppTest do Streamlit.

Existem por causa de um defeito real: a aba de lote anunciava o modelo padrão do
campus mesmo com TI1 ou TI3 selecionados, porque lia `campus.template` em vez de
`campus.template_para(disciplina)`. A criação estava correta — só o texto mentia —,
e nenhum teste de modelo ou de controlador pegaria isso.
"""
import pytest
import requests
import streamlit as st
from streamlit.testing.v1 import AppTest

CAMINHO_DA_APLICACAO = "app/main.py"

# Modelo esperado por disciplina no Coração Eucarístico, escrito de forma independente
# do cadastro para que uma divergência entre tela e configuração apareça aqui.
MODELO_ESPERADO = {
    "TI1": "ICEI-PUC-Minas-PMGES-TI/ti1-es-template-repository",
    "TI2": "ICEI-PUC-Minas-PMGES-TI/TI-ES-GenericTemplate",
    "TI3": "ICEI-PUC-Minas-PMGES-TI/ti3-es-template-repository",
    "TI6": "ICEI-PUC-Minas-PMGES-TI/TI-ES-GenericTemplate",
}


class RespostaFalsa:
    def __init__(self, status_code, dados=None, headers=None):
        self.status_code = status_code
        self._dados = dados
        self.text = ""
        self.headers = headers or {}

    def json(self):
        return self._dados


@pytest.fixture
def aplicacao(monkeypatch) -> AppTest:
    """Sobe a aplicação com a API do GitHub simulada e o token já informado."""
    def get(url, headers=None, params=None, allow_redirects=None):
        if url.endswith("/members") or url.endswith("/teams"):
            return RespostaFalsa(200, [], {})
        return RespostaFalsa(404, {})

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(st, "file_uploader", lambda *a, **k: None)
    st.cache_data.clear()

    at = AppTest.from_file(CAMINHO_DA_APLICACAO, default_timeout=90).run()
    [campo for campo in at.text_input if "Token" in campo.label][0].set_value("token-de-teste")
    return at.run()


def legendas_de_modelo(at: AppTest):
    """Retorna as legendas da tela que mencionam o repositório-modelo."""
    return [c.value for c in at.caption if "modelo" in c.value.lower()]


class TestLegendaDoModelo:

    @pytest.mark.parametrize("disciplina", list(MODELO_ESPERADO))
    def test_a_aba_de_lote_anuncia_o_modelo_da_disciplina(self, aplicacao, disciplina):
        seletores = {s.key: s for s in aplicacao.selectbox}
        seletores["disciplina_lote"].set_value(disciplina)
        aplicacao.run()

        legendas = [linha for linha in legendas_de_modelo(aplicacao) if "Repositório-modelo" in linha]

        assert legendas, "a aba de lote não anunciou nenhum repositório-modelo"
        assert MODELO_ESPERADO[disciplina] in legendas[0]

    @pytest.mark.parametrize("disciplina", list(MODELO_ESPERADO))
    def test_a_aba_individual_anuncia_o_modelo_da_disciplina(self, aplicacao, disciplina):
        seletores = {s.key: s for s in aplicacao.selectbox}
        seletores["disciplina"].set_value(disciplina)
        aplicacao.run()

        campo = [c for c in aplicacao.text_input if c.label == "Nome do repositório"][0]
        campo.set_value("Adota Pet")
        aplicacao.run()

        legendas = [linha for linha in legendas_de_modelo(aplicacao) if linha.startswith("Privado")]

        assert legendas, "a aba individual não anunciou nenhum repositório-modelo"
        assert MODELO_ESPERADO[disciplina] in legendas[0]

    def test_as_duas_abas_anunciam_o_mesmo_modelo(self, aplicacao):
        seletores = {s.key: s for s in aplicacao.selectbox}
        seletores["disciplina"].set_value("TI1")
        seletores["disciplina_lote"].set_value("TI1")
        aplicacao.run()

        campo = [c for c in aplicacao.text_input if c.label == "Nome do repositório"][0]
        campo.set_value("Adota Pet")
        aplicacao.run()

        legendas = legendas_de_modelo(aplicacao)
        esperado = MODELO_ESPERADO["TI1"]

        assert len(legendas) == 2
        assert all(esperado in linha for linha in legendas)


class TestAbas:

    def test_a_aplicacao_sobe_sem_erro(self, aplicacao):
        assert aplicacao.exception == []

    def test_as_abas_de_adicao_ficam_a_direita_das_de_criacao(self, aplicacao):
        rotulos = [aba.label for aba in aplicacao.tabs]

        assert rotulos == [
            "Repositório individual",
            "Criação em lote",
            "Adicionar aluno",
            "Adicionar alunos por arquivo",
        ]
