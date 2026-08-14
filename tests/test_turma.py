import pytest

from app.models.campus import CAMPI
from app.models.disciplina import Disciplina
from app.models.turma import (
    CODIGOS_POR_TURMA,
    Turno,
    codigo_valido,
    listar_codigos,
    listar_disciplinas,
    listar_turnos,
)

# Espelho do catálogo informado pela coordenação, escrito de forma independente para
# que uma alteração acidental no cadastro seja detectada.
CATALOGO_ESPERADO = {
    "pmg": {
        "TI1": {"M": ["0427100", "0427200"], "N": ["0438100", "0438200"]},
        "TI2": {"M": ["8183100", "8183200"], "N": ["8243100", "8243200"]},
        "TI3": {"M": ["9545100"], "N": ["9577100"]},
        "TI4": {"M": ["3126100"], "N": ["3170100"]},
        "TI5": {"N": ["6904100"]},
        "TI6": {"N": ["9623100"]},
    },
    "plf": {
        "TI1": {"M": ["7620100"], "N": ["7641100"]},
        "TI2": {"M": ["7587100"], "N": ["7600100"]},
        "TI3": {"M": ["8966100"], "N": ["5533100"]},
        "TI4": {"M": ["1247100"], "N": ["1254100"]},
        "TI5": {"N": ["0492100"]},
        "TI6": {"N": ["8508100"]},
    },
}

TURNO_POR_LETRA = {"M": Turno.MANHA, "N": Turno.NOITE}


def casos_de_codigo():
    for sigla, disciplinas in CATALOGO_ESPERADO.items():
        for rotulo, turnos in disciplinas.items():
            for letra, codigos in turnos.items():
                yield sigla, rotulo, letra, codigos


class TestCatalogo:

    @pytest.mark.parametrize("sigla, rotulo, letra, esperados", list(casos_de_codigo()))
    def test_codigos_cadastrados(self, sigla, rotulo, letra, esperados):
        assert listar_codigos(sigla, Disciplina[rotulo], TURNO_POR_LETRA[letra]) == esperados

    def test_todas_as_disciplinas_sao_ofertadas_nos_dois_campi(self):
        for sigla in CATALOGO_ESPERADO:
            assert listar_disciplinas(sigla) == list(Disciplina)

    @pytest.mark.parametrize("sigla", ["pmg", "plf"])
    @pytest.mark.parametrize("rotulo", ["TI5", "TI6"])
    def test_ti5_e_ti6_apenas_a_noite(self, sigla, rotulo):
        assert listar_turnos(sigla, Disciplina[rotulo]) == [Turno.NOITE]

    @pytest.mark.parametrize("sigla", ["pmg", "plf"])
    @pytest.mark.parametrize("rotulo", ["TI1", "TI2", "TI3", "TI4"])
    def test_ti1_a_ti4_nos_dois_turnos(self, sigla, rotulo):
        assert listar_turnos(sigla, Disciplina[rotulo]) == [Turno.MANHA, Turno.NOITE]

    def test_manha_aparece_antes_da_noite(self):
        assert listar_turnos("pmg", Disciplina.TI1) == [Turno.MANHA, Turno.NOITE]

    def test_o_catalogo_cobre_exatamente_os_campi_cadastrados(self):
        assert sorted(CODIGOS_POR_TURMA) == sorted(campus.sigla for campus in CAMPI.values())

    def test_codigos_com_zero_a_esquerda_sao_preservados(self):
        # '0427100' e '0492100' perderiam o zero se fossem tratados como número.
        assert "0427100" in listar_codigos("pmg", Disciplina.TI1, Turno.MANHA)
        assert "0492100" in listar_codigos("plf", Disciplina.TI5, Turno.NOITE)

    def test_nao_ha_codigo_repetido_dentro_do_campus(self):
        for sigla, disciplinas in CODIGOS_POR_TURMA.items():
            codigos = [c for turnos in disciplinas.values() for cs in turnos.values() for c in cs]
            assert len(codigos) == len(set(codigos)), f"código repetido em {sigla}"

    def test_todos_os_codigos_sao_numericos(self):
        from app.utils import github_utils

        for disciplinas in CODIGOS_POR_TURMA.values():
            for turnos in disciplinas.values():
                for codigos in turnos.values():
                    for codigo in codigos:
                        assert github_utils.validar_codigo_disciplina(codigo)


class TestConsultasSemCadastro:

    def test_campus_desconhecido_nao_quebra(self):
        assert listar_disciplinas("xxx") == []
        assert listar_turnos("xxx", Disciplina.TI1) == []
        assert listar_codigos("xxx", Disciplina.TI1, Turno.MANHA) == []

    def test_turno_sem_oferta_devolve_lista_vazia(self):
        assert listar_codigos("pmg", Disciplina.TI5, Turno.MANHA) == []


class TestValidacaoDeCodigo:

    def test_codigo_do_catalogo_e_valido(self):
        assert codigo_valido("pmg", "9623100") is True

    def test_codigo_de_outro_campus_nao_vale(self):
        # 9623100 é TI6 do Coração Eucarístico; em Lourdes o TI6 é 8508100.
        assert codigo_valido("plf", "9623100") is False

    def test_codigo_inventado_nao_vale(self):
        assert codigo_valido("pmg", "0000000") is False


class TestChaveDeVerificacaoDoLote:
    """
    A verificação prévia é reaproveitada enquanto a chave não muda. Se a turma ficasse
    de fora dela, trocar a disciplina reaproveitaria nomes de repositório antigos.
    """

    @staticmethod
    def chave(organizacao="org", disciplina=Disciplina.TI1, codigo="0427100", conteudo="Repositorio: X"):
        from app.views.criacao_lote_view import chave_de_verificacao
        return chave_de_verificacao(organizacao, disciplina, codigo, conteudo)

    def test_mesmos_dados_geram_a_mesma_chave(self):
        assert self.chave() == self.chave()

    def test_trocar_a_disciplina_muda_a_chave(self):
        assert self.chave(disciplina=Disciplina.TI6) != self.chave()

    def test_trocar_o_codigo_da_turma_muda_a_chave(self):
        assert self.chave(codigo="9623100") != self.chave()

    def test_trocar_a_organizacao_muda_a_chave(self):
        assert self.chave(organizacao="outra") != self.chave()

    def test_trocar_o_arquivo_muda_a_chave(self):
        assert self.chave(conteudo="Repositorio: Y") != self.chave()
