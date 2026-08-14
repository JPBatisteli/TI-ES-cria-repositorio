import pytest

from app.models.arquivo_lote import ArquivoLote
from app.models.campus import obter_campus
from app.models.disciplina import Disciplina

ARQUIVO_VALIDO = """# Turma da manhã
Repositorio: Adota Pet
Grupo: Grupo 1
Membros: ana-souza, bruno-lima, carla-dias

Repositorio: Brechó Re-Use
Grupo: Grupo 2
Membros: joao-silva, maria-dev
"""


class TestCabecalhoObsoleto:
    """A turma deixou de vir do arquivo; os rótulos antigos são ignorados com aviso."""

    @pytest.mark.parametrize("rotulo", ["TI", "ti", "Disciplina", "Codigo", "Código",
                                        "Codigo da disciplina"])
    def test_rotulos_de_turma_sao_ignorados_sem_erro(self, rotulo):
        arquivo = ArquivoLote.de_texto(f"{rotulo}: qualquer coisa\nRepositorio: X\n")

        assert arquivo.valido is True
        assert len(arquivo.grupos) == 1

    def test_o_professor_e_avisado_de_que_a_turma_vem_da_interface(self):
        arquivo = ArquivoLote.de_texto("TI: TI1\nCodigo: 2401100\nRepositorio: X\n")

        assert arquivo.valido is True
        assert len(arquivo.avisos) == 1
        assert "escolhida na interface" in arquivo.avisos[0]
        assert "linha 1" in arquivo.avisos[0]
        assert "linha 2" in arquivo.avisos[0]

    def test_arquivo_sem_rotulos_antigos_nao_gera_aviso(self):
        arquivo = ArquivoLote.de_texto("Repositorio: X\nMembros: ana\n")

        assert arquivo.avisos == []

    def test_valor_do_rotulo_antigo_e_descartado(self):
        # Mesmo um valor absurdo não impede o processamento: a linha é ignorada.
        arquivo = ArquivoLote.de_texto("TI: TI99\nCodigo: nao-numerico\nRepositorio: X\n")

        assert arquivo.valido is True


class TestLeituraDosGrupos:

    def test_le_todos_os_grupos_na_ordem(self):
        arquivo = ArquivoLote.de_texto(ARQUIVO_VALIDO)

        assert [grupo.nome_repositorio for grupo in arquivo.grupos] == ["Adota Pet", "Brechó Re-Use"]
        assert [grupo.nome_grupo for grupo in arquivo.grupos] == ["Grupo 1", "Grupo 2"]

    def test_le_os_membros_separados_por_virgula(self):
        arquivo = ArquivoLote.de_texto(ARQUIVO_VALIDO)

        assert [aluno.username for aluno in arquivo.grupos[0].membros] == [
            "ana-souza", "bruno-lima", "carla-dias"
        ]

    def test_aceita_ponto_e_virgula_como_separador(self):
        arquivo = ArquivoLote.de_texto("Repositorio: X\nMembros: ana; bruno\n")
        assert [aluno.username for aluno in arquivo.grupos[0].membros] == ["ana", "bruno"]

    def test_remove_arroba_dos_nomes_de_usuario(self):
        arquivo = ArquivoLote.de_texto("Repositorio: X\nMembros: @ana, @bruno\n")
        assert [aluno.username for aluno in arquivo.grupos[0].membros] == ["ana", "bruno"]

    def test_membros_em_varias_linhas_sao_acumulados(self):
        conteudo = "Repositorio: X\nMembros: ana, bruno\nMembros: carla\n"
        arquivo = ArquivoLote.de_texto(conteudo)

        assert [aluno.username for aluno in arquivo.grupos[0].membros] == ["ana", "bruno", "carla"]

    def test_linhas_em_branco_sao_opcionais(self):
        conteudo = (
            ""
            "Repositorio: A\nGrupo: G1\nMembros: ana\n"
            "Repositorio: B\nGrupo: G2\nMembros: bruno\n"
        )
        arquivo = ArquivoLote.de_texto(conteudo)

        assert arquivo.valido is True
        assert len(arquivo.grupos) == 2

    def test_comentarios_sao_ignorados(self):
        conteudo = "# comentário\nTI: TI1\nCodigo: 123\n# outro\nRepositorio: X\n"
        arquivo = ArquivoLote.de_texto(conteudo)

        assert arquivo.valido is True
        assert len(arquivo.grupos) == 1

    def test_total_de_alunos_soma_todos_os_grupos(self):
        assert ArquivoLote.de_texto(ARQUIVO_VALIDO).total_alunos == 5


class TestErrosDeFormato:

    def test_linha_sem_rotulo_e_reportada(self):
        arquivo = ArquivoLote.de_texto("Repositorio: X\nana-souza\n")

        assert arquivo.valido is False
        assert any("Linha 2" in erro and "Rótulo: valor" in erro for erro in arquivo.erros)

    def test_rotulo_desconhecido_e_reportado(self):
        arquivo = ArquivoLote.de_texto("Repositorio: X\nProfessor: Joao\n")

        assert arquivo.valido is False
        assert any("rótulo desconhecido" in erro and "Professor" in erro for erro in arquivo.erros)

    def test_membros_antes_do_primeiro_repositorio_e_reportado(self):
        arquivo = ArquivoLote.de_texto("Membros: ana\nRepositorio: X\n")

        assert arquivo.valido is False
        assert any("antes de qualquer" in erro for erro in arquivo.erros)

    def test_arquivo_sem_grupos_e_reportado(self):
        arquivo = ArquivoLote.de_texto("TI: TI1\nCodigo: 2401100\n")

        assert arquivo.valido is False
        assert any("Nenhum grupo" in erro for erro in arquivo.erros)

    def test_repositorios_repetidos_sao_reportados(self):
        conteudo = (
            ""
            "Repositorio: Adota Pet\nMembros: ana\n"
            "Repositorio: adota pet\nMembros: bruno\n"
        )
        arquivo = ArquivoLote.de_texto(conteudo)

        assert arquivo.valido is False
        assert any("repete" in erro for erro in arquivo.erros)

    def test_nome_de_repositorio_sem_caracteres_validos_e_reportado(self):
        arquivo = ArquivoLote.de_texto("Repositorio: !!!\n")

        assert arquivo.valido is False
        assert any("não gera um" in erro for erro in arquivo.erros)


class TestAvisos:

    def test_grupo_sem_membros_gera_aviso_mas_nao_erro(self):
        arquivo = ArquivoLote.de_texto("Repositorio: X\nGrupo: G1\n")

        assert arquivo.valido is True
        assert any("sem membros" in aviso for aviso in arquivo.grupos[0].avisos)

    def test_grupo_sem_nome_gera_aviso(self):
        arquivo = ArquivoLote.de_texto("Repositorio: X\nMembros: ana\n")

        assert arquivo.valido is True
        assert any("sem nome" in aviso for aviso in arquivo.grupos[0].avisos)

    def test_username_invalido_gera_aviso(self):
        arquivo = ArquivoLote.de_texto("Repositorio: X\nMembros: joao--silva\n")

        assert arquivo.valido is True
        assert any("inválidos" in aviso for aviso in arquivo.grupos[0].avisos)

    def test_grupo_completo_nao_gera_avisos(self):
        arquivo = ArquivoLote.de_texto(ARQUIVO_VALIDO)
        assert arquivo.grupos[0].avisos == []


class TestMontagemDasSolicitacoes:

    def test_gera_uma_solicitacao_por_grupo(self):
        arquivo = ArquivoLote.de_texto(ARQUIVO_VALIDO)
        solicitacoes = arquivo.montar_solicitacoes(obter_campus("Coração Eucarístico"), Disciplina.TI1, "2401100")

        assert len(solicitacoes) == 2

    def test_nome_do_repositorio_segue_o_padrao(self):
        arquivo = ArquivoLote.de_texto(ARQUIVO_VALIDO)
        solicitacoes = arquivo.montar_solicitacoes(obter_campus("Coração Eucarístico"), Disciplina.TI1, "2401100")
        periodo = solicitacoes[0].periodo_letivo_atual

        assert solicitacoes[0].nome == (
            f"pmg-es-{periodo.ano}-{periodo.semestre}-ti1-2401100-adota-pet"
        )

    def test_nome_do_grupo_vira_o_nome_da_equipe(self):
        arquivo = ArquivoLote.de_texto(ARQUIVO_VALIDO)
        solicitacoes = arquivo.montar_solicitacoes(obter_campus("Lourdes"), Disciplina.TI1, "2401100")

        assert solicitacoes[0].criar_equipe is True
        assert solicitacoes[0].nome_equipe == "Grupo 1"

    def test_grupo_sem_nome_recai_no_nome_derivado(self):
        arquivo = ArquivoLote.de_texto("Repositorio: X\nMembros: ana\n")
        solicitacao = arquivo.montar_solicitacoes(obter_campus("Lourdes"), Disciplina.TI1, "2401100")[0]

        assert solicitacao.nome_equipe == solicitacao.nome_equipe_derivado

    def test_campus_selecionado_define_a_organizacao(self):
        arquivo = ArquivoLote.de_texto(ARQUIVO_VALIDO)
        solicitacoes = arquivo.montar_solicitacoes(obter_campus("Lourdes"), Disciplina.TI1, "2401100")

        assert solicitacoes[0].campus.organizacao == "ICEI-PUC-Minas-PPLES-TI"
        assert solicitacoes[0].nome.startswith("plf-")

    def test_solicitacoes_geradas_sao_validas(self):
        arquivo = ArquivoLote.de_texto(ARQUIVO_VALIDO)

        for solicitacao in arquivo.montar_solicitacoes(obter_campus("Coração Eucarístico"), Disciplina.TI1, "2401100"):
            assert solicitacao.validar() is True


class TestArquivoDeExemplo:
    """Garante que o exemplo distribuído com o projeto continua sendo válido."""

    @staticmethod
    def carregar() -> ArquivoLote:
        from app.views.criacao_lote_view import ARQUIVO_DE_EXEMPLO
        return ArquivoLote.de_texto(ARQUIVO_DE_EXEMPLO.read_text(encoding="utf-8"))

    def test_o_arquivo_de_exemplo_existe(self):
        from app.views.criacao_lote_view import ARQUIVO_DE_EXEMPLO
        assert ARQUIVO_DE_EXEMPLO.is_file()

    def test_o_arquivo_de_exemplo_e_lido_sem_erros(self):
        arquivo = self.carregar()

        assert arquivo.valido is True
        assert arquivo.erros == []

    def test_o_arquivo_de_exemplo_nao_gera_avisos(self):
        for grupo in self.carregar().grupos:
            assert grupo.avisos == []

    def test_as_solicitacoes_do_exemplo_sao_validas(self):
        arquivo = self.carregar()
        solicitacoes = arquivo.montar_solicitacoes(obter_campus("Coração Eucarístico"), Disciplina.TI1, "2401100")

        assert len(solicitacoes) == len(arquivo.grupos)
        for solicitacao in solicitacoes:
            assert solicitacao.validar() is True

    def test_o_modelo_oferecido_na_interface_e_o_arquivo_de_exemplo(self):
        from app.views.criacao_lote_view import ARQUIVO_DE_EXEMPLO, carregar_modelo_de_arquivo
        assert carregar_modelo_de_arquivo() == ARQUIVO_DE_EXEMPLO.read_text(encoding="utf-8")


class TestVisibilidade:
    """Os repositórios de TI são sempre privados; não há opção para torná-los públicos."""

    @pytest.mark.parametrize("campus", ["Coração Eucarístico", "Lourdes"])
    def test_todos_os_repositorios_do_lote_sao_privados(self, campus):
        arquivo = ArquivoLote.de_texto(ARQUIVO_VALIDO)
        solicitacoes = arquivo.montar_solicitacoes(obter_campus(campus), Disciplina.TI1, "2401100")

        assert len(solicitacoes) == 2
        assert all(solicitacao.privado for solicitacao in solicitacoes)

    def test_a_visibilidade_nao_e_configuravel(self):
        import inspect

        parametros = inspect.signature(ArquivoLote.montar_solicitacoes).parameters
        assert "privado" not in parametros
