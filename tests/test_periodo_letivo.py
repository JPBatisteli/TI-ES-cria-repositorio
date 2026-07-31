from datetime import date

import pytest

from app.models.campus import obter_campus
from app.models.disciplina import Disciplina
from app.models.novo_repositorio import NovoRepositorio
from app.models.periodo_letivo import PeriodoLetivo


class TestPeriodoAtual:

    @pytest.mark.parametrize("data, ano, semestre", [
        (date(2026, 1, 1), 2026, 1),    # primeiro dia do ano
        (date(2026, 3, 15), 2026, 1),   # meio do primeiro semestre
        (date(2026, 7, 9), 2026, 1),    # véspera do último dia
        (date(2026, 7, 10), 2026, 1),   # último dia do primeiro semestre
        (date(2026, 7, 11), 2026, 2),   # primeiro dia do segundo semestre
        (date(2026, 9, 30), 2026, 2),   # meio do segundo semestre
        (date(2026, 12, 31), 2026, 2),  # último dia do ano
        (date(2027, 1, 1), 2027, 1),    # virada de ano
    ])
    def test_determina_o_periodo_pela_data(self, data, ano, semestre):
        periodo = PeriodoLetivo.atual(data)
        assert (periodo.ano, periodo.semestre) == (ano, semestre)

    def test_dia_10_de_julho_ainda_pertence_ao_primeiro_semestre(self):
        assert PeriodoLetivo.atual(date(2026, 7, 10)).semestre == 1

    def test_dia_11_de_julho_ja_pertence_ao_segundo_semestre(self):
        assert PeriodoLetivo.atual(date(2026, 7, 11)).semestre == 2

    def test_sem_data_informada_usa_o_dia_de_hoje(self):
        assert PeriodoLetivo.atual() == PeriodoLetivo.atual(date.today())

    def test_representacao_textual(self):
        assert str(PeriodoLetivo(2026, 2)) == "2026/2"


class TestValidacaoDoPeriodo:

    @staticmethod
    def criar_solicitacao(ano: int, semestre: int) -> NovoRepositorio:
        return NovoRepositorio(
            campus=obter_campus("Coração Eucarístico"),
            disciplina=Disciplina.TI1,
            codigo_disciplina="2401100",
            nome_projeto="Adota Pet",
            ano=ano,
            semestre=semestre,
            periodo_letivo_atual=PeriodoLetivo(2026, 2)
        )

    def test_periodo_atual_e_aceito(self):
        assert self.criar_solicitacao(2026, 2).validar() is True

    @pytest.mark.parametrize("ano, semestre", [
        (2026, 1),  # semestre já encerrado
        (2025, 2),  # ano anterior
        (2027, 1),  # semestre futuro
        (2027, 2),  # ano futuro
    ])
    def test_periodo_diferente_do_atual_e_rejeitado(self, ano, semestre):
        solicitacao = self.criar_solicitacao(ano, semestre)

        assert solicitacao.validar() is False
        assert "O período letivo deve ser o atual (2026/2)." in solicitacao.erros

    @pytest.mark.parametrize("semestre", [0, 3])
    def test_semestre_invalido_continua_rejeitado(self, semestre):
        assert self.criar_solicitacao(2026, semestre).validar() is False

    def test_periodo_padrao_e_o_do_dia_de_hoje(self):
        solicitacao = NovoRepositorio(
            campus=obter_campus("Lourdes"),
            disciplina=Disciplina.TI1,
            codigo_disciplina="2401100",
            nome_projeto="Adota Pet"
        )

        assert solicitacao.periodo_letivo_atual == PeriodoLetivo.atual()
        assert (solicitacao.ano, solicitacao.semestre) == (
            PeriodoLetivo.atual().ano,
            PeriodoLetivo.atual().semestre,
        )
        assert solicitacao.validar() is True
