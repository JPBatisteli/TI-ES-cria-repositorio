import pytest
import requests

from app.controllers.adicao_membros_controller import AdicaoMembrosController
from app.models.aluno import Aluno
from app.models.lista_de_usuarios import ListaDeUsuarios
from app.models.resultado_adicao_membro import ResultadoAdicaoMembro, SituacaoMembro
from app.services.github_service import GithubService, GithubServiceError

from test_github_service import RespostaFalsa


class GithubServiceFalso:
    """Dublê do GithubService, usado para testar a adição sem acessar a API."""

    def __init__(self, membros=(), contas=(), pendentes=(), erro_ao_listar="", erro_ao_convidar=""):
        self.membros = {n.lower() for n in membros}
        self.contas = {n.lower() for n in contas} | self.membros
        self.pendentes = {n.lower() for n in pendentes}
        self.erro_ao_listar = erro_ao_listar
        self.erro_ao_convidar = erro_ao_convidar
        self.convidados = []
        self.consultas_de_membro = []
        self.listagens = 0

    def listar_membros(self, nome_organizacao, papel="member"):
        self.listagens += 1
        if self.erro_ao_listar:
            raise GithubServiceError(self.erro_ao_listar)
        return list(self.membros)

    def e_membro(self, nome_organizacao, username):
        self.consultas_de_membro.append(username)
        return username.lower() in self.membros

    def usuario_existe(self, username):
        return username.lower() in self.contas

    def adicionar_membro_na_organizacao(self, nome_organizacao, username, papel="member"):
        if self.erro_ao_convidar:
            raise GithubServiceError(self.erro_ao_convidar)
        self.convidados.append((username, papel))
        return "active" if username.lower() in self.pendentes else "pending"


def criar_controller(service) -> AdicaoMembrosController:
    controller = AdicaoMembrosController(token="token-de-teste")
    controller.github_service = service
    return controller


class TestLeituraDaLista:

    def test_um_nome_por_linha(self):
        lista = ListaDeUsuarios.de_texto("ana-souza\nbruno-lima\n")
        assert [a.username for a in lista.alunos] == ["ana-souza", "bruno-lima"]

    def test_comentarios_e_linhas_vazias_sao_ignorados(self):
        lista = ListaDeUsuarios.de_texto("# turma TI1\n\nana-souza\n\n# fim\n")
        assert [a.username for a in lista.alunos] == ["ana-souza"]

    def test_arroba_inicial_e_removido(self):
        assert ListaDeUsuarios.de_texto("@ana-souza\n").alunos[0].username == "ana-souza"

    @pytest.mark.parametrize("separador", [",", ";"])
    def test_varios_nomes_na_mesma_linha(self, separador):
        lista = ListaDeUsuarios.de_texto(f"ana{separador} bruno\n")
        assert [a.username for a in lista.alunos] == ["ana", "bruno"]

    def test_repetidos_sao_considerados_uma_vez_e_avisados(self):
        lista = ListaDeUsuarios.de_texto("ana-souza\nbruno\nANA-SOUZA\n")

        assert [a.username for a in lista.alunos] == ["ana-souza", "bruno"]
        assert len(lista.avisos) == 1
        assert "linha 3" in lista.avisos[0]

    def test_arquivo_sem_nomes_e_rejeitado(self):
        lista = ListaDeUsuarios.de_texto("# só comentário\n\n")

        assert lista.valido is False
        assert "Nenhum nome de usuário" in lista.erros[0]

    def test_nomes_invalidos_sao_lidos_e_sinalizados(self):
        lista = ListaDeUsuarios.de_texto("ana-souza\njoao--silva\n")

        assert lista.valido is True
        assert lista.invalidos == ["joao--silva"]


class TestAdicaoIndividual:

    def test_aluno_fora_da_organizacao_e_convidado(self):
        service = GithubServiceFalso(contas=["ana"])
        resultado = criar_controller(service).adicionar_membro("org", Aluno("ana"))

        assert resultado.situacao == SituacaoMembro.CONVITE_ENVIADO
        assert resultado.sucesso is True
        assert service.convidados == [("ana", "member")]

    def test_quem_ja_e_membro_nao_recebe_convite(self):
        service = GithubServiceFalso(membros=["ana"])
        resultado = criar_controller(service).adicionar_membro("org", Aluno("ana"))

        assert resultado.situacao == SituacaoMembro.JA_ERA_MEMBRO
        assert resultado.sucesso is True
        assert service.convidados == []

    def test_conta_inexistente_nao_gera_convite(self):
        service = GithubServiceFalso()
        resultado = criar_controller(service).adicionar_membro("org", Aluno("fantasma"))

        assert resultado.situacao == SituacaoMembro.CONTA_INEXISTENTE
        assert resultado.sucesso is False
        assert service.convidados == []

    def test_username_invalido_nao_consulta_a_api(self):
        service = GithubServiceFalso()
        resultado = criar_controller(service).adicionar_membro("org", Aluno("joao--silva"))

        assert resultado.situacao == SituacaoMembro.USERNAME_INVALIDO
        assert service.consultas_de_membro == []

    def test_estado_ativo_e_reportado_como_entrada(self):
        service = GithubServiceFalso(contas=["ana"], pendentes=["ana"])
        resultado = criar_controller(service).adicionar_membro("org", Aluno("ana"))

        assert resultado.situacao == SituacaoMembro.ENTROU

    def test_erro_da_api_e_reportado(self):
        service = GithubServiceFalso(contas=["ana"], erro_ao_convidar="Sem permissão.")
        resultado = criar_controller(service).adicionar_membro("org", Aluno("ana"))

        assert resultado.situacao == SituacaoMembro.ERRO
        assert "Sem permissão" in resultado.descricao


class TestAdicaoEmLote:

    def test_convida_apenas_quem_esta_fora(self):
        service = GithubServiceFalso(membros=["ana"], contas=["bruno", "carla"])
        alunos = [Aluno("ana"), Aluno("bruno"), Aluno("carla")]

        resultados = criar_controller(service).adicionar_membros("org", alunos)

        situacoes = {r.aluno.username: r.situacao for r in resultados}
        assert situacoes["ana"] == SituacaoMembro.JA_ERA_MEMBRO
        assert situacoes["bruno"] == SituacaoMembro.CONVITE_ENVIADO
        assert [n for n, _ in service.convidados] == ["bruno", "carla"]

    def test_a_lista_de_membros_e_carregada_uma_unica_vez(self):
        service = GithubServiceFalso(membros=["ana"], contas=["bruno", "carla"])
        alunos = [Aluno("ana"), Aluno("bruno"), Aluno("carla")]

        criar_controller(service).adicionar_membros("org", alunos)

        assert service.listagens == 1
        assert service.consultas_de_membro == []

    def test_falha_em_um_aluno_nao_interrompe_os_demais(self):
        class ServiceInstavel(GithubServiceFalso):
            def adicionar_membro_na_organizacao(self, nome_organizacao, username, papel="member"):
                if username == "bruno":
                    raise GithubServiceError("Falha temporária.")
                return super().adicionar_membro_na_organizacao(nome_organizacao, username, papel)

        service = ServiceInstavel(contas=["ana", "bruno", "carla"])
        resultados = criar_controller(service).adicionar_membros(
            "org", [Aluno("ana"), Aluno("bruno"), Aluno("carla")]
        )

        situacoes = {r.aluno.username: r.situacao for r in resultados}
        assert situacoes["bruno"] == SituacaoMembro.ERRO
        assert situacoes["ana"] == SituacaoMembro.CONVITE_ENVIADO
        assert situacoes["carla"] == SituacaoMembro.CONVITE_ENVIADO

    def test_falha_ao_listar_marca_todos_sem_convidar_ninguem(self):
        service = GithubServiceFalso(erro_ao_listar="Token inválido.")
        resultados = criar_controller(service).adicionar_membros("org", [Aluno("ana"), Aluno("bruno")])

        assert all(r.situacao == SituacaoMembro.ERRO for r in resultados)
        assert service.convidados == []

    def test_progresso_e_informado_a_cada_aluno(self):
        service = GithubServiceFalso(contas=["ana", "bruno"])
        indices = []

        criar_controller(service).adicionar_membros(
            "org", [Aluno("ana"), Aluno("bruno")],
            ao_concluir_cada=lambda i, r: indices.append(i)
        )

        assert indices == [0, 1]

    def test_lista_vazia_nao_gera_chamadas(self):
        service = GithubServiceFalso()
        assert criar_controller(service).adicionar_membros("org", []) == []
        assert service.listagens == 0


class TestServicoDeAdicaoNaOrganizacao:

    @pytest.fixture
    def service(self) -> GithubService:
        return GithubService(token="token-de-teste")

    def test_usa_a_rota_de_associacao_da_organizacao(self, service, monkeypatch):
        capturado = {}

        def put_falso(url, headers=None, json=None):
            capturado["url"] = url
            capturado["json"] = json
            return RespostaFalsa(200, {"state": "pending"})

        monkeypatch.setattr(requests, "put", put_falso)
        service.adicionar_membro_na_organizacao("org", "ana")

        assert capturado["url"] == "https://api.github.com/orgs/org/memberships/ana"
        assert capturado["json"] == {"role": "member"}

    def test_devolve_o_estado_da_associacao(self, service, monkeypatch):
        monkeypatch.setattr(requests, "put", lambda *a, **k: RespostaFalsa(200, {"state": "pending"}))
        assert service.adicionar_membro_na_organizacao("org", "ana") == "pending"

    def test_falha_e_propagada(self, service, monkeypatch):
        monkeypatch.setattr(requests, "put", lambda *a, **k: RespostaFalsa(403, {}))

        with pytest.raises(GithubServiceError, match="Sem permissão"):
            service.adicionar_membro_na_organizacao("org", "ana")


class TestDescricoes:

    @pytest.mark.parametrize("situacao, trecho", [
        (SituacaoMembro.CONVITE_ENVIADO, "precisa aceitá-lo"),
        (SituacaoMembro.JA_ERA_MEMBRO, "Já era membro"),
        (SituacaoMembro.ENTROU, "Entrou na organização"),
        (SituacaoMembro.USERNAME_INVALIDO, "inválido"),
        (SituacaoMembro.CONTA_INEXISTENTE, "Confira a grafia"),
    ])
    def test_cada_situacao_tem_mensagem_propria(self, situacao, trecho):
        resultado = ResultadoAdicaoMembro(aluno=Aluno("ana"), situacao=situacao)
        assert trecho in resultado.descricao

    def test_erro_usa_o_detalhe_recebido(self):
        resultado = ResultadoAdicaoMembro(
            aluno=Aluno("ana"), situacao=SituacaoMembro.ERRO, detalhe="Token expirado."
        )
        assert resultado.descricao == "Token expirado."


class TestCacheDaListagemDeMembros:
    """
    A listagem fica em cache para não recarregar a cada interação, mas o prazo precisa
    ser curto: a composição da organização muda durante o próprio uso da ferramenta.
    """

    def test_o_prazo_e_de_poucos_minutos(self):
        from app.views.criacao_repositorio_view import SEGUNDOS_DE_CACHE_DOS_MEMBROS

        assert SEGUNDOS_DE_CACHE_DOS_MEMBROS == 300
        assert SEGUNDOS_DE_CACHE_DOS_MEMBROS <= 600, "prazo longo demais para a lista mudar em uso"

    def test_a_listagem_pode_ser_descartada_sob_demanda(self):
        from app.views.criacao_repositorio_view import carregar_membros_organizacao

        # É o que o botão "Atualizar lista" e a adição de alunos chamam.
        assert hasattr(carregar_membros_organizacao, "clear")
