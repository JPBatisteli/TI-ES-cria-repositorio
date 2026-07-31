import pytest

from app.models.campus import obter_campus
from app.models.disciplina import Disciplina
from app.models.novo_repositorio import NovoRepositorio
from app.models.periodo_letivo import PeriodoLetivo
from app.utils import github_utils


def criar_solicitacao(**alteracoes) -> NovoRepositorio:
    """Cria uma solicitação válida, permitindo sobrescrever campos individualmente."""
    dados = {
        "campus": obter_campus("Coração Eucarístico"),
        "disciplina": Disciplina.TI2,
        "codigo_disciplina": "3687100",
        "nome_projeto": "Brechó Re-Use",
        "ano": 2025,
        "semestre": 1,
        "periodo_letivo_atual": PeriodoLetivo(2025, 1),
    }
    dados.update(alteracoes)
    return NovoRepositorio(**dados)


class TestGerarSlug:

    @pytest.mark.parametrize("texto, esperado", [
        ("Brechó Re-Use", "brecho-re-use"),
        ("Fabiana Móveis", "fabiana-moveis"),
        ("  Lar Dorcas  ", "lar-dorcas"),
        ("Grupo 2 — Livremente", "grupo-2-livremente"),
        ("PSI+", "psi"),
        ("já-em-slug", "ja-em-slug"),
    ])
    def test_converte_texto_livre_em_slug(self, texto, esperado):
        assert github_utils.gerar_slug(texto) == esperado

    def test_texto_sem_caracteres_alfanumericos_gera_slug_vazio(self):
        assert github_utils.gerar_slug("!!! ???") == ""


class TestNomePadronizado:

    def test_nome_segue_o_padrao_adotado(self):
        solicitacao = criar_solicitacao()
        assert solicitacao.nome == "pmg-es-2025-1-ti2-3687100-brecho-re-use"

    def test_campus_determina_a_sigla_e_a_organizacao(self):
        solicitacao = criar_solicitacao(
            campus=obter_campus("Lourdes"),
            disciplina=Disciplina.TI3,
            codigo_disciplina="898110",
            nome_projeto="Grupo 2 Livremente"
        )
        assert solicitacao.nome == "plf-es-2025-1-ti3-898110-grupo-2-livremente"
        assert solicitacao.campus.organizacao == "ICEI-PUC-Minas-PPLES-TI"

    def test_prefixo_identifica_a_turma(self):
        assert criar_solicitacao().prefixo == "pmg-es-2025-1-ti2-3687100"

    def test_nome_gerado_e_reconhecido_pelo_parse(self):
        dados = github_utils.parse_nome_repositorio(criar_solicitacao().nome)
        assert dados == {
            "sigla": "pmg",
            "ano": "2025",
            "semestre": "1",
            "disciplina": "ti2",
            "codigo": "3687100",
            "projeto": "brecho-re-use",
        }


class TestValidacao:

    def test_solicitacao_completa_e_valida(self):
        solicitacao = criar_solicitacao()
        assert solicitacao.validar() is True
        assert solicitacao.erros == []

    @pytest.mark.parametrize("codigo", ["", "   ", "24A1100", "2401-100"])
    def test_codigo_da_disciplina_deve_conter_apenas_digitos(self, codigo):
        solicitacao = criar_solicitacao(codigo_disciplina=codigo)
        assert solicitacao.validar() is False
        assert solicitacao.erros

    def test_nome_do_projeto_e_obrigatorio(self):
        solicitacao = criar_solicitacao(nome_projeto="   ")
        assert solicitacao.validar() is False

    def test_nome_do_projeto_sem_caracteres_validos_e_rejeitado(self):
        solicitacao = criar_solicitacao(nome_projeto="!!!")
        assert solicitacao.validar() is False

    @pytest.mark.parametrize("semestre", [0, 3])
    def test_semestre_fora_de_1_e_2_e_rejeitado(self, semestre):
        solicitacao = criar_solicitacao(semestre=semestre)
        assert solicitacao.validar() is False

    @pytest.mark.parametrize("ano, semestre", [(2019, 1), (2024, 2), (2030, 1)])
    def test_periodo_diferente_do_atual_e_rejeitado(self, ano, semestre):
        # As regras de período letivo são detalhadas em tests/test_periodo_letivo.py.
        solicitacao = criar_solicitacao(ano=ano, semestre=semestre)
        assert solicitacao.validar() is False

    def test_nome_excedendo_o_limite_do_github_e_rejeitado(self):
        solicitacao = criar_solicitacao(nome_projeto="projeto " * 20)
        assert solicitacao.validar() is False
        assert any("limite" in erro for erro in solicitacao.erros)

    def test_validar_reinicia_a_lista_de_erros(self):
        solicitacao = criar_solicitacao(codigo_disciplina="abc")
        assert solicitacao.validar() is False

        solicitacao.codigo_disciplina = "3687100"
        assert solicitacao.validar() is True
        assert solicitacao.erros == []
