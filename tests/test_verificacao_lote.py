import pytest

from app.controllers.criacao_repositorio_controller import CriacaoRepositorioController
from app.models.arquivo_lote import ArquivoLote
from app.models.campus import obter_campus
from app.services.github_service import GithubServiceError

ARQUIVO = """TI: TI1
Codigo: 2401100

Repositorio: Adota Pet
Grupo: Grupo 1
Membros: ana-souza, bruno-lima

Repositorio: Brechó Re-Use
Grupo: Grupo 2
Membros: carla-dias
"""


class GithubServiceFalso:
    """Dublê do GithubService, usado para testar a verificação sem acessar a API."""

    def __init__(self, membros=(), equipes=(), repositorios=(), contas=(), erro_ao_listar=""):
        self.membros = list(membros)
        self.equipes = list(equipes)
        self.repositorios = {nome.lower() for nome in repositorios}
        self.contas = {nome.lower() for nome in contas} | {nome.lower() for nome in membros}
        self.erro_ao_listar = erro_ao_listar
        self.consultas_de_conta = []

    def listar_membros(self, nome_organizacao, papel="member"):
        if self.erro_ao_listar:
            raise GithubServiceError(self.erro_ao_listar)
        return self.membros

    def listar_equipes(self, nome_organizacao):
        return self.equipes

    def repositorio_existe(self, nome_organizacao, nome_repositorio):
        return nome_repositorio.lower() in self.repositorios

    def usuario_existe(self, username):
        self.consultas_de_conta.append(username)
        return username.lower() in self.contas


def verificar(service, conteudo=ARQUIVO, campus="Coração Eucarístico"):
    controller = CriacaoRepositorioController(token="token-de-teste")
    controller.github_service = service
    solicitacoes = ArquivoLote.de_texto(conteudo).montar_solicitacoes(obter_campus(campus))
    return controller.verificar_lote(solicitacoes)


class TestArquivoSemImpedimentos:

    def test_todos_os_grupos_ficam_aptos(self):
        verificacao = verificar(GithubServiceFalso(membros=["ana-souza", "bruno-lima", "carla-dias"]))

        assert verificacao.apto is True
        assert verificacao.grupos_com_impedimento == []

    def test_conta_os_alunos_encontrados(self):
        verificacao = verificar(GithubServiceFalso(membros=["ana-souza", "bruno-lima", "carla-dias"]))

        assert verificacao.total_alunos_encontrados == 3
        assert verificacao.total_alunos == 3

    def test_nao_consulta_contas_de_quem_ja_e_membro(self):
        service = GithubServiceFalso(membros=["ana-souza", "bruno-lima", "carla-dias"])
        verificar(service)

        assert service.consultas_de_conta == []


def nome_do_primeiro_repositorio(conteudo: str = ARQUIVO) -> str:
    """Devolve o nome gerado para o primeiro grupo, que depende do período letivo."""
    solicitacoes = ArquivoLote.de_texto(conteudo).montar_solicitacoes(obter_campus("Coração Eucarístico"))
    return solicitacoes[0].nome


class TestNomeDoRepositorio:

    def test_repositorio_existente_impede_a_criacao(self):
        service = GithubServiceFalso(
            membros=["ana-souza", "bruno-lima", "carla-dias"],
            repositorios=[nome_do_primeiro_repositorio()]
        )
        verificacao = verificar(service)

        assert verificacao.apto is False
        assert verificacao.grupos[0].repositorio_disponivel is False
        assert any("já existe na organização" in imp for imp in verificacao.grupos[0].impedimentos)

    def test_demais_grupos_permanecem_aptos(self):
        service = GithubServiceFalso(
            membros=["ana-souza", "bruno-lima", "carla-dias"],
            repositorios=[nome_do_primeiro_repositorio()]
        )
        verificacao = verificar(service)

        assert verificacao.grupos[0].apto is False
        assert verificacao.grupos[1].apto is True


class TestNomeDaEquipe:

    def test_equipe_existente_impede_a_criacao(self):
        service = GithubServiceFalso(
            membros=["ana-souza", "bruno-lima", "carla-dias"],
            equipes=["grupo-1"]
        )
        verificacao = verificar(service)

        assert verificacao.apto is False
        assert verificacao.grupos[0].equipe_disponivel is False
        assert verificacao.grupos[1].equipe_disponivel is True

    def test_comparacao_de_equipe_ignora_acentos_e_maiusculas(self):
        conteudo = "TI: TI1\nCodigo: 123\nRepositorio: X\nGrupo: Equipe Brechó\nMembros: ana\n"
        service = GithubServiceFalso(membros=["ana"], equipes=["equipe-brecho"])

        verificacao = verificar(service, conteudo=conteudo)

        assert verificacao.grupos[0].equipe_disponivel is False


class TestSituacaoDosAlunos:

    def test_aluno_com_conta_fora_da_organizacao(self):
        service = GithubServiceFalso(membros=["ana-souza", "bruno-lima"], contas=["carla-dias"])
        verificacao = verificar(service)

        assert verificacao.grupos[1].alunos_fora_da_organizacao == ["carla-dias"]
        assert any("Fora da organização" in imp for imp in verificacao.grupos[1].impedimentos)

    def test_aluno_sem_conta_no_github(self):
        service = GithubServiceFalso(membros=["ana-souza", "bruno-lima"])
        verificacao = verificar(service)

        assert verificacao.grupos[1].alunos_inexistentes == ["carla-dias"]
        assert any("Não existe no GitHub" in imp for imp in verificacao.grupos[1].impedimentos)

    def test_username_invalido_nao_gera_consulta(self):
        conteudo = "TI: TI1\nCodigo: 123\nRepositorio: X\nGrupo: G\nMembros: joao--silva\n"
        service = GithubServiceFalso()

        verificacao = verificar(service, conteudo=conteudo)

        assert verificacao.grupos[0].alunos_invalidos == ["joao--silva"]
        assert service.consultas_de_conta == []

    def test_mesmo_aluno_em_varios_grupos_e_consultado_uma_vez(self):
        conteudo = (
            "TI: TI1\nCodigo: 123\n"
            "Repositorio: A\nGrupo: G1\nMembros: repetido\n"
            "Repositorio: B\nGrupo: G2\nMembros: repetido\n"
        )
        service = GithubServiceFalso()

        verificar(service, conteudo=conteudo)

        assert service.consultas_de_conta == ["repetido"]

    def test_dica_quando_nenhum_aluno_pertence_a_organizacao(self):
        service = GithubServiceFalso(contas=["ana-souza", "bruno-lima", "carla-dias"])
        verificacao = verificar(service)

        assert verificacao.nenhum_aluno_encontrado is True

    def test_sem_dica_quando_ao_menos_um_aluno_e_encontrado(self):
        service = GithubServiceFalso(membros=["ana-souza"], contas=["bruno-lima", "carla-dias"])
        verificacao = verificar(service)

        assert verificacao.nenhum_aluno_encontrado is False


class TestFalhaNaVerificacao:

    def test_erro_ao_carregar_as_listas_marca_todos_os_grupos(self):
        service = GithubServiceFalso(erro_ao_listar="Token do GitHub inválido ou expirado.")
        verificacao = verificar(service)

        assert verificacao.apto is False
        assert len(verificacao.grupos_com_impedimento) == 2
        for grupo in verificacao.grupos:
            assert "Token do GitHub inválido" in grupo.erro

    def test_lista_vazia_nao_fica_apta(self):
        controller = CriacaoRepositorioController(token="token-de-teste")
        controller.github_service = GithubServiceFalso()

        assert controller.verificar_lote([]).apto is False
