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


ARQUIVO_TRES_GRUPOS = """TI: TI1
Codigo: 2401100

Repositorio: Projeto A
Grupo: Grupo A
Membros: ana-souza

Repositorio: Projeto B
Grupo: Grupo B
Membros: bruno-lima

Repositorio: Projeto C
Grupo: Grupo C
Membros: carla-dias
"""

TODOS_OS_MEMBROS = ["ana-souza", "bruno-lima", "carla-dias"]


def nomes_gerados(conteudo: str = ARQUIVO_TRES_GRUPOS):
    """Nomes de repositório e de equipe gerados, que dependem do período letivo."""
    solicitacoes = ArquivoLote.de_texto(conteudo).montar_solicitacoes(obter_campus("Coração Eucarístico"))
    return [(s.nome, s.nome_equipe) for s in solicitacoes]


class TestRetomadaDeLoteInterrompido:
    """Um lote que falhou no meio deve poder continuar sem editar o arquivo."""

    def test_grupos_ja_criados_nao_bloqueiam_os_restantes(self):
        criados = [nome for nome, _ in nomes_gerados()[:2]]
        service = GithubServiceFalso(
            membros=TODOS_OS_MEMBROS,
            equipes=[equipe.lower().replace(" ", "-") for _, equipe in nomes_gerados()[:2]],
            repositorios=criados
        )
        verificacao = verificar(service, conteudo=ARQUIVO_TRES_GRUPOS)

        assert verificacao.pode_criar is True
        assert verificacao.e_retomada is True
        assert len(verificacao.grupos_ja_criados) == 2
        assert len(verificacao.grupos_a_criar) == 1

    def test_apenas_os_pendentes_sao_enviados_para_criacao(self):
        criados = [nome for nome, _ in nomes_gerados()[:2]]
        service = GithubServiceFalso(
            membros=TODOS_OS_MEMBROS,
            equipes=[equipe.lower().replace(" ", "-") for _, equipe in nomes_gerados()[:2]],
            repositorios=criados
        )
        verificacao = verificar(service, conteudo=ARQUIVO_TRES_GRUPOS)

        pendentes = verificacao.solicitacoes_a_criar()
        assert [s.nome for s in pendentes] == [nomes_gerados()[2][0]]

    def test_problema_real_continua_bloqueando_mesmo_com_retomada(self):
        criados = [nome for nome, _ in nomes_gerados()[:2]]
        # carla-dias não está na organização: problema a corrigir, não grupo concluído.
        service = GithubServiceFalso(
            membros=["ana-souza", "bruno-lima"],
            contas=["carla-dias"],
            repositorios=criados
        )
        verificacao = verificar(service, conteudo=ARQUIVO_TRES_GRUPOS)

        assert verificacao.pode_criar is False
        assert len(verificacao.grupos_com_problema) == 1

    def test_lote_totalmente_criado_nao_libera_a_criacao(self):
        service = GithubServiceFalso(
            membros=TODOS_OS_MEMBROS,
            equipes=[equipe.lower().replace(" ", "-") for _, equipe in nomes_gerados()],
            repositorios=[nome for nome, _ in nomes_gerados()]
        )
        verificacao = verificar(service, conteudo=ARQUIVO_TRES_GRUPOS)

        assert verificacao.pode_criar is False
        assert verificacao.e_retomada is False
        assert len(verificacao.grupos_a_criar) == 0

    def test_primeira_execucao_nao_e_retomada(self):
        service = GithubServiceFalso(membros=TODOS_OS_MEMBROS)
        verificacao = verificar(service, conteudo=ARQUIVO_TRES_GRUPOS)

        assert verificacao.e_retomada is False
        assert verificacao.pode_criar is True
        assert verificacao.apto is True
        assert len(verificacao.grupos_a_criar) == 3


class TestGrupoIncompleto:
    """Repositório criado sem equipe indica interrupção no meio do grupo."""

    def test_repositorio_sem_equipe_e_sinalizado(self):
        service = GithubServiceFalso(
            membros=TODOS_OS_MEMBROS,
            repositorios=[nomes_gerados()[0][0]]   # repositório criado, equipe não
        )
        verificacao = verificar(service, conteudo=ARQUIVO_TRES_GRUPOS)

        assert verificacao.grupos[0].possivelmente_incompleto is True
        assert len(verificacao.grupos_possivelmente_incompletos) == 1

    def test_grupo_completo_nao_e_sinalizado(self):
        equipe = nomes_gerados()[0][1].lower().replace(" ", "-")
        service = GithubServiceFalso(
            membros=TODOS_OS_MEMBROS,
            repositorios=[nomes_gerados()[0][0]],
            equipes=[equipe]
        )
        verificacao = verificar(service, conteudo=ARQUIVO_TRES_GRUPOS)

        assert verificacao.grupos[0].possivelmente_incompleto is False

    def test_equipe_ocupada_sem_repositorio_continua_sendo_problema(self):
        equipe = nomes_gerados()[0][1].lower().replace(" ", "-")
        service = GithubServiceFalso(membros=TODOS_OS_MEMBROS, equipes=[equipe])
        verificacao = verificar(service, conteudo=ARQUIVO_TRES_GRUPOS)

        assert verificacao.grupos[0].problemas
        assert verificacao.pode_criar is False
