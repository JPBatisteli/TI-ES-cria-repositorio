import pytest

from app.controllers.criacao_repositorio_controller import CriacaoRepositorioController
from app.models.aluno import Aluno
from app.models.campus import obter_campus
from app.models.disciplina import Disciplina
from app.models.novo_repositorio import NovoRepositorio
from app.models.periodo_letivo import PeriodoLetivo
from app.models.resultado_adicao_aluno import SituacaoAluno
from app.services.github_service import GithubServiceError


class GithubServiceFalso:
    """Dublê do GithubService, usado para testar a adição de alunos sem acessar a API."""

    def __init__(self, membros=None, erro_ao_adicionar: str = "", convites=()):
        self.membros = {nome.lower() for nome in (membros or [])}
        self.erro_ao_adicionar = erro_ao_adicionar
        self.convites = {nome.lower() for nome in convites}
        self.adicionados = []

    def repositorio_existe(self, nome_organizacao, nome_repositorio):
        return False

    def criar_repositorio(self, nome_organizacao, nome_repositorio, descricao="",
                          privado=False, inicializar_readme=True):
        return {"html_url": f"https://github.com/{nome_organizacao}/{nome_repositorio}"}

    def criar_repositorio_por_template(self, template_owner, template_repositorio, nome_organizacao,
                                       nome_repositorio, descricao="", privado=False,
                                       incluir_todas_as_branches=False):
        return self.criar_repositorio(nome_organizacao, nome_repositorio, descricao, privado)

    def e_membro(self, nome_organizacao, username):
        return username.lower() in self.membros

    def adicionar_colaborador(self, nome_organizacao, nome_repositorio, username, permissao="push"):
        if self.erro_ao_adicionar:
            raise GithubServiceError(self.erro_ao_adicionar)
        self.adicionados.append((username, permissao))
        return username.lower() in self.convites


def criar_solicitacao(usernames) -> NovoRepositorio:
    return NovoRepositorio(
        campus=obter_campus("Coração Eucarístico"),
        disciplina=Disciplina.TI1,
        codigo_disciplina="2401100",
        nome_projeto="Adota Pet",
        ano=2025,
        semestre=1,
        periodo_letivo_atual=PeriodoLetivo(2025, 1),
        alunos=[Aluno.de_texto(username) for username in usernames]
    )


def criar_controller(service) -> CriacaoRepositorioController:
    controller = CriacaoRepositorioController(token="token-de-teste")
    controller.github_service = service
    return controller


class TestAluno:

    @pytest.mark.parametrize("texto, esperado", [
        ("@joaosilva", "joaosilva"),
        ("  maria-dev  ", "maria-dev"),
        ("Pedro2003", "Pedro2003"),
    ])
    def test_limpa_o_texto_informado(self, texto, esperado):
        assert Aluno.de_texto(texto).username == esperado

    @pytest.mark.parametrize("username", ["joaosilva", "maria-dev", "a", "Pedro2003", "a1-b2-c3"])
    def test_aceita_nomes_de_usuario_validos(self, username):
        assert Aluno(username).valido is True

    @pytest.mark.parametrize("username", ["", "-joao", "joao-", "joao--silva", "joão", "a" * 40, "joao silva"])
    def test_rejeita_nomes_de_usuario_invalidos(self, username):
        assert Aluno(username).valido is False

    def test_comparacao_ignora_maiusculas(self):
        assert Aluno("JoaoSilva").username_normalizado == Aluno("joaosilva").username_normalizado


class TestAlunosUnicos:

    def test_remove_repeticoes_preservando_a_ordem(self):
        solicitacao = criar_solicitacao(["ana", "bruno", "ANA", "carla", "bruno"])
        assert [aluno.username for aluno in solicitacao.alunos_unicos] == ["ana", "bruno", "carla"]


class TestAdicaoDeAlunos:

    def test_membro_da_organizacao_recebe_acesso_de_escrita(self):
        service = GithubServiceFalso(membros=["ana", "bruno"])
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(["ana", "bruno"]))

        assert resultado.sucesso is True
        assert [item.situacao for item in resultado.alunos] == [SituacaoAluno.ACESSO_CONCEDIDO] * 2
        assert service.adicionados == [("ana", "push"), ("bruno", "push")]

    def test_aluno_fora_da_organizacao_e_reportado_sem_tentar_adicionar(self):
        service = GithubServiceFalso(membros=["ana"])
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(["ana", "calouro"]))

        situacoes = {item.aluno.username: item.situacao for item in resultado.alunos}
        assert situacoes["ana"] == SituacaoAluno.ACESSO_CONCEDIDO
        assert situacoes["calouro"] == SituacaoAluno.FORA_DA_ORGANIZACAO
        assert service.adicionados == [("ana", "push")]

    def test_mensagem_orienta_o_professor_sobre_o_aluno_ausente(self):
        service = GithubServiceFalso(membros=[])
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(["calouro"]))

        assert "Não faz parte da organização" in resultado.alunos[0].descricao

    def test_convite_pendente_e_distinguido_do_acesso_imediato(self):
        service = GithubServiceFalso(membros=["ana"], convites=["ana"])
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(["ana"]))

        assert resultado.alunos[0].situacao == SituacaoAluno.CONVITE_ENVIADO
        assert resultado.alunos[0].sucesso is True

    def test_username_invalido_nao_gera_chamada_a_api(self):
        service = GithubServiceFalso(membros=["ana"])
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(["joao--silva"]))

        assert resultado.alunos[0].situacao == SituacaoAluno.USERNAME_INVALIDO
        assert service.adicionados == []

    def test_falha_em_um_aluno_nao_interrompe_os_demais(self):
        class ServiceInstavel(GithubServiceFalso):
            def adicionar_colaborador(self, nome_organizacao, nome_repositorio, username, permissao="push"):
                if username == "bruno":
                    raise GithubServiceError("Falha temporária na API.")
                return super().adicionar_colaborador(nome_organizacao, nome_repositorio, username, permissao)

        service = ServiceInstavel(membros=["ana", "bruno", "carla"])
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(["ana", "bruno", "carla"]))

        situacoes = {item.aluno.username: item.situacao for item in resultado.alunos}
        assert situacoes["bruno"] == SituacaoAluno.ERRO
        assert situacoes["ana"] == SituacaoAluno.ACESSO_CONCEDIDO
        assert situacoes["carla"] == SituacaoAluno.ACESSO_CONCEDIDO

    def test_repositorio_permanece_criado_mesmo_sem_nenhum_aluno_adicionado(self):
        service = GithubServiceFalso(membros=[])
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(["ana", "bruno"]))

        assert resultado.sucesso is True
        assert resultado.total_alunos_adicionados == 0
        assert len(resultado.alunos_com_problema) == 2

    def test_repositorio_sem_alunos_continua_funcionando(self):
        service = GithubServiceFalso(membros=["ana"])
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao([]))

        assert resultado.sucesso is True
        assert resultado.alunos == []
