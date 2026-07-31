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
    """Dublê do GithubService, usado para testar o fluxo por equipe sem acessar a API."""

    def __init__(self, membros=None, erro_ao_criar_equipe: str = "", pendentes=()):
        self.membros = {nome.lower() for nome in (membros or [])}
        self.erro_ao_criar_equipe = erro_ao_criar_equipe
        self.pendentes = {nome.lower() for nome in pendentes}
        self.equipes_criadas = []
        self.permissoes = []
        self.membros_da_equipe = []
        self.colaboradores = []

    def repositorio_existe(self, nome_organizacao, nome_repositorio):
        return False

    def criar_repositorio(self, nome_organizacao, nome_repositorio, descricao="",
                          privado=False, inicializar_readme=True):
        return {"html_url": f"https://github.com/{nome_organizacao}/{nome_repositorio}"}

    def criar_equipe(self, nome_organizacao, nome_equipe, descricao="", privacidade="closed"):
        if self.erro_ao_criar_equipe:
            raise GithubServiceError(self.erro_ao_criar_equipe)
        self.equipes_criadas.append((nome_organizacao, nome_equipe, privacidade))
        return nome_equipe.lower()

    def definir_permissao_da_equipe(self, nome_organizacao, slug_equipe, nome_repositorio, permissao="admin"):
        self.permissoes.append((slug_equipe, nome_repositorio, permissao))

    def adicionar_membro_na_equipe(self, nome_organizacao, slug_equipe, username, papel="member"):
        self.membros_da_equipe.append((slug_equipe, username, papel))
        return "pending" if username.lower() in self.pendentes else "active"

    def e_membro(self, nome_organizacao, username):
        return username.lower() in self.membros

    def adicionar_colaborador(self, nome_organizacao, nome_repositorio, username, permissao="push"):
        self.colaboradores.append((username, permissao))
        return False


def criar_solicitacao(usernames=(), criar_equipe=True, nome_equipe="") -> NovoRepositorio:
    return NovoRepositorio(
        campus=obter_campus("Coração Eucarístico"),
        disciplina=Disciplina.TI2,
        codigo_disciplina="3687100",
        nome_projeto="Brechó Re-Use",
        ano=2025,
        semestre=1,
        periodo_letivo_atual=PeriodoLetivo(2025, 1),
        alunos=[Aluno.de_texto(username) for username in usernames],
        criar_equipe=criar_equipe,
        nome_equipe_personalizado=nome_equipe
    )


def criar_controller(service) -> CriacaoRepositorioController:
    controller = CriacaoRepositorioController(token="token-de-teste")
    controller.github_service = service
    return controller


class TestNomeDaEquipe:

    def test_sem_nome_informado_a_equipe_recebe_o_nome_do_repositorio(self):
        solicitacao = criar_solicitacao()
        assert solicitacao.nome_equipe == "pmg-es-2025-1-ti2-3687100-brecho-re-use"
        assert solicitacao.equipe_com_nome_personalizado is False

    def test_nome_informado_pelo_professor_prevalece(self):
        solicitacao = criar_solicitacao(nome_equipe="Equipe Brechó")
        assert solicitacao.nome_equipe == "Equipe Brechó"
        assert solicitacao.equipe_com_nome_personalizado is True

    @pytest.mark.parametrize("nome_informado", ["", "   ", "\t"])
    def test_nome_em_branco_recai_no_nome_derivado(self, nome_informado):
        solicitacao = criar_solicitacao(nome_equipe=nome_informado)
        assert solicitacao.nome_equipe == solicitacao.nome_equipe_derivado
        assert solicitacao.equipe_com_nome_personalizado is False

    def test_espacos_em_volta_do_nome_informado_sao_removidos(self):
        assert criar_solicitacao(nome_equipe="  Equipe Brechó  ").nome_equipe == "Equipe Brechó"

    def test_nome_derivado_permanece_acessivel_mesmo_com_nome_informado(self):
        solicitacao = criar_solicitacao(nome_equipe="Equipe Brechó")
        assert solicitacao.nome_equipe_derivado == "pmg-es-2025-1-ti2-3687100-brecho-re-use"

    def test_equipe_e_criada_com_o_nome_informado(self):
        service = GithubServiceFalso()
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(nome_equipe="Equipe Brechó"))

        assert service.equipes_criadas[0][1] == "Equipe Brechó"
        assert resultado.equipe == "equipe brechó"


class TestCriacaoDaEquipe:

    def test_cria_a_equipe_e_torna_a_administradora_do_repositorio(self):
        service = GithubServiceFalso(membros=["ana"])
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(["ana"]))

        assert resultado.sucesso is True
        assert resultado.equipe == "pmg-es-2025-1-ti2-3687100-brecho-re-use"
        assert resultado.erro_equipe == ""
        assert service.permissoes == [
            ("pmg-es-2025-1-ti2-3687100-brecho-re-use", "pmg-es-2025-1-ti2-3687100-brecho-re-use", "admin")
        ]

    def test_equipe_e_criada_como_visivel_para_permitir_aninhamento(self):
        service = GithubServiceFalso()
        criar_controller(service).criar_repositorio(criar_solicitacao())

        assert service.equipes_criadas[0][2] == "closed"

    def test_alunos_entram_na_equipe_e_nao_como_colaboradores(self):
        service = GithubServiceFalso(membros=["ana", "bruno"])
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(["ana", "bruno"]))

        assert [item.situacao for item in resultado.alunos] == [SituacaoAluno.ADICIONADO_A_EQUIPE] * 2
        assert [nome for _, nome, _ in service.membros_da_equipe] == ["ana", "bruno"]
        assert service.colaboradores == []

    def test_aluno_fora_da_organizacao_nao_e_adicionado_a_equipe(self):
        service = GithubServiceFalso(membros=["ana"])
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(["ana", "calouro"]))

        situacoes = {item.aluno.username: item.situacao for item in resultado.alunos}
        assert situacoes["calouro"] == SituacaoAluno.FORA_DA_ORGANIZACAO
        assert [nome for _, nome, _ in service.membros_da_equipe] == ["ana"]

    def test_username_invalido_nao_gera_chamada_a_api(self):
        service = GithubServiceFalso(membros=["ana"])
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(["joao--silva"]))

        assert resultado.alunos[0].situacao == SituacaoAluno.USERNAME_INVALIDO
        assert service.membros_da_equipe == []

    def test_estado_pendente_e_reportado_como_convite(self):
        service = GithubServiceFalso(membros=["ana"], pendentes=["ana"])
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(["ana"]))

        assert resultado.alunos[0].situacao == SituacaoAluno.CONVITE_ENVIADO
        assert resultado.alunos[0].sucesso is True


class TestFalhaNaCriacaoDaEquipe:

    def test_repositorio_permanece_criado_e_o_erro_e_reportado(self):
        service = GithubServiceFalso(membros=["ana"], erro_ao_criar_equipe="Name must be unique for this org.")
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(["ana"]))

        assert resultado.sucesso is True
        assert resultado.equipe == ""
        assert "Name must be unique" in resultado.erro_equipe

    def test_alunos_recebem_acesso_individual_quando_a_equipe_falha(self):
        service = GithubServiceFalso(membros=["ana"], erro_ao_criar_equipe="Falha.")
        resultado = criar_controller(service).criar_repositorio(criar_solicitacao(["ana"]))

        assert service.colaboradores == [("ana", "push")]
        assert resultado.alunos[0].situacao == SituacaoAluno.ACESSO_CONCEDIDO


class TestSemEquipe:

    def test_opcao_desmarcada_mantem_o_fluxo_de_colaborador_individual(self):
        service = GithubServiceFalso(membros=["ana"])
        resultado = criar_controller(service).criar_repositorio(
            criar_solicitacao(["ana"], criar_equipe=False)
        )

        assert resultado.equipe == ""
        assert resultado.erro_equipe == ""
        assert service.equipes_criadas == []
        assert service.colaboradores == [("ana", "push")]


class TestCriacaoEmLote:

    def test_cria_todos_os_repositorios_na_ordem(self):
        service = GithubServiceFalso(membros=["ana", "bruno"])
        solicitacoes = [
            criar_solicitacao(["ana"], nome_equipe="Grupo 1"),
            criar_solicitacao(["bruno"], nome_equipe="Grupo 2"),
        ]
        solicitacoes[1].nome_projeto = "Adota Pet"

        resultados = criar_controller(service).criar_repositorios_em_lote(solicitacoes)

        assert [r.sucesso for r in resultados] == [True, True]
        assert [nome for _, nome, _ in service.equipes_criadas] == ["Grupo 1", "Grupo 2"]

    def test_falha_em_um_repositorio_nao_interrompe_os_demais(self):
        class ServiceInstavel(GithubServiceFalso):
            def criar_repositorio(self, nome_organizacao, nome_repositorio, descricao="",
                                  privado=False, inicializar_readme=True):
                if "adota-pet" in nome_repositorio:
                    raise GithubServiceError("Falha temporária na API.")
                return super().criar_repositorio(nome_organizacao, nome_repositorio, descricao,
                                                 privado, inicializar_readme)

        service = ServiceInstavel(membros=["ana"])
        primeira = criar_solicitacao(["ana"], nome_equipe="Grupo 1")
        segunda = criar_solicitacao(["ana"], nome_equipe="Grupo 2")
        segunda.nome_projeto = "Adota Pet"
        terceira = criar_solicitacao(["ana"], nome_equipe="Grupo 3")
        terceira.nome_projeto = "Psi Plus"

        resultados = criar_controller(service).criar_repositorios_em_lote([primeira, segunda, terceira])

        assert [r.sucesso for r in resultados] == [True, False, True]
        assert resultados[1].erros == ["Falha temporária na API."]

    def test_progresso_e_informado_a_cada_repositorio(self):
        service = GithubServiceFalso(membros=["ana"])
        solicitacoes = [criar_solicitacao(["ana"], nome_equipe="Grupo 1")]
        solicitacoes.append(criar_solicitacao(["ana"], nome_equipe="Grupo 2"))
        solicitacoes[1].nome_projeto = "Adota Pet"

        avisos = []
        criar_controller(service).criar_repositorios_em_lote(
            solicitacoes, ao_concluir_cada=lambda indice, resultado: avisos.append(indice)
        )

        assert avisos == [0, 1]

    def test_lista_vazia_nao_gera_chamadas(self):
        service = GithubServiceFalso()
        assert criar_controller(service).criar_repositorios_em_lote([]) == []
        assert service.equipes_criadas == []
