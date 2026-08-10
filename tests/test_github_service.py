import time

import pytest
import requests

from app.services.github_service import GithubService, GithubServiceError, RepositorioJaExisteError


class RespostaFalsa:
    """Dublê de requests.Response, usado para simular respostas da API do GitHub."""

    def __init__(self, status_code: int, dados=None, texto: str = "", headers=None):
        self.status_code = status_code
        self._dados = dados
        self.text = texto
        self.headers = headers or {}

    def json(self):
        if self._dados is None:
            raise ValueError("Resposta sem corpo JSON.")
        return self._dados


@pytest.fixture
def service() -> GithubService:
    return GithubService(token="token-de-teste")


def test_token_informado_sobrescreve_o_token_do_ambiente():
    assert GithubService(token="token-de-teste").headers["Authorization"] == "token token-de-teste"


def test_repositorio_existente_retorna_verdadeiro(service, monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: RespostaFalsa(200, {}))
    assert service.repositorio_existe("org", "repo") is True


def test_repositorio_inexistente_retorna_falso(service, monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: RespostaFalsa(404, {}))
    assert service.repositorio_existe("org", "repo") is False


@pytest.mark.parametrize("status, trecho_esperado", [
    (401, "Token do GitHub inválido"),
    (403, "Sem permissão"),
])
def test_erros_de_autenticacao_geram_mensagens_especificas(service, monkeypatch, status, trecho_esperado):
    monkeypatch.setattr(requests, "get", lambda *a, **k: RespostaFalsa(status, {}))

    with pytest.raises(GithubServiceError, match=trecho_esperado):
        service.repositorio_existe("org", "repo")


def test_criacao_bem_sucedida_retorna_os_dados_do_repositorio(service, monkeypatch):
    dados = {"html_url": "https://github.com/org/repo"}
    monkeypatch.setattr(requests, "post", lambda *a, **k: RespostaFalsa(201, dados))

    assert service.criar_repositorio("org", "repo") == dados


def test_nome_duplicado_levanta_excecao_especifica(service, monkeypatch):
    dados = {"message": "Repository creation failed.", "errors": [{"message": "name already exists on this account"}]}
    monkeypatch.setattr(requests, "post", lambda *a, **k: RespostaFalsa(422, dados))

    with pytest.raises(RepositorioJaExisteError):
        service.criar_repositorio("org", "repo")


def test_outro_erro_422_nao_e_tratado_como_duplicidade(service, monkeypatch):
    dados = {"message": "Repository creation failed.", "errors": [{"message": "name is invalid"}]}
    monkeypatch.setattr(requests, "post", lambda *a, **k: RespostaFalsa(422, dados))

    with pytest.raises(GithubServiceError, match="name is invalid") as excecao:
        service.criar_repositorio("org", "repo")

    assert not isinstance(excecao.value, RepositorioJaExisteError)


def test_envia_os_parametros_esperados_para_a_api(service, monkeypatch):
    capturado = {}

    def post_falso(url, headers=None, json=None):
        capturado["url"] = url
        capturado["json"] = json
        return RespostaFalsa(201, {"html_url": "https://github.com/org/repo"})

    monkeypatch.setattr(requests, "post", post_falso)

    service.criar_repositorio("org", "repo", descricao="TI", privado=True, inicializar_readme=False)

    assert capturado["url"] == "https://api.github.com/orgs/org/repos"
    assert capturado["json"] == {
        "name": "repo",
        "description": "TI",
        "private": True,
        "auto_init": False,
    }


class TestListagemDeMembros:

    def test_percorre_todas_as_paginas(self, service, monkeypatch):
        paginas = {
            1: RespostaFalsa(200, [{"login": "carla"}, {"login": "ana"}], headers={"Link": '<...>; rel="next"'}),
            2: RespostaFalsa(200, [{"login": "Bruno"}], headers={}),
        }

        def get_falso(url, headers=None, params=None):
            return paginas[params["page"]]

        monkeypatch.setattr(requests, "get", get_falso)

        assert service.listar_membros("org") == ["ana", "Bruno", "carla"]

    def test_filtra_pelo_papel_de_membro_excluindo_os_proprietarios(self, service, monkeypatch):
        capturado = {}

        def get_falso(url, headers=None, params=None):
            capturado.update(params)
            return RespostaFalsa(200, [], headers={})

        monkeypatch.setattr(requests, "get", get_falso)
        service.listar_membros("org")

        assert capturado["role"] == "member"


class TestVerificacaoDeMembro:

    def test_status_204_indica_que_o_usuario_e_membro(self, service, monkeypatch):
        monkeypatch.setattr(requests, "get", lambda *a, **k: RespostaFalsa(204))
        assert service.e_membro("org", "ana") is True

    def test_status_404_indica_que_o_usuario_nao_e_membro(self, service, monkeypatch):
        monkeypatch.setattr(requests, "get", lambda *a, **k: RespostaFalsa(404))
        assert service.e_membro("org", "calouro") is False

    def test_status_302_indica_que_o_token_nao_pertence_a_organizacao(self, service, monkeypatch):
        monkeypatch.setattr(requests, "get", lambda *a, **k: RespostaFalsa(302))

        with pytest.raises(GithubServiceError, match="não pertence à organização"):
            service.e_membro("org", "ana")

    def test_nao_segue_redirecionamentos(self, service, monkeypatch):
        capturado = {}

        def get_falso(url, headers=None, allow_redirects=None):
            capturado["allow_redirects"] = allow_redirects
            return RespostaFalsa(204)

        monkeypatch.setattr(requests, "get", get_falso)
        service.e_membro("org", "ana")

        assert capturado["allow_redirects"] is False


class TestAdicaoDeColaborador:

    def test_status_201_indica_convite_pendente(self, service, monkeypatch):
        monkeypatch.setattr(requests, "put", lambda *a, **k: RespostaFalsa(201, {}))
        assert service.adicionar_colaborador("org", "repo", "ana") is True

    def test_status_204_indica_acesso_imediato(self, service, monkeypatch):
        monkeypatch.setattr(requests, "put", lambda *a, **k: RespostaFalsa(204))
        assert service.adicionar_colaborador("org", "repo", "ana") is False

    def test_envia_a_permissao_de_escrita_por_padrao(self, service, monkeypatch):
        capturado = {}

        def put_falso(url, headers=None, json=None):
            capturado["url"] = url
            capturado["json"] = json
            return RespostaFalsa(204)

        monkeypatch.setattr(requests, "put", put_falso)
        service.adicionar_colaborador("org", "repo", "ana")

        assert capturado["url"] == "https://api.github.com/repos/org/repo/collaborators/ana"
        assert capturado["json"] == {"permission": "push"}

    def test_erro_da_api_e_propagado(self, service, monkeypatch):
        monkeypatch.setattr(requests, "put", lambda *a, **k: RespostaFalsa(403, {}))

        with pytest.raises(GithubServiceError, match="Sem permissão"):
            service.adicionar_colaborador("org", "repo", "ana")

    def test_permite_incluir_os_proprietarios_na_listagem(self, service, monkeypatch):
        capturado = {}

        def get_falso(url, headers=None, params=None):
            capturado.update(params)
            return RespostaFalsa(200, [], headers={})

        monkeypatch.setattr(requests, "get", get_falso)
        service.listar_membros("org", papel="all")

        assert capturado["role"] == "all"


class TestEquipes:

    def test_criacao_devolve_o_slug_gerado_pelo_github(self, service, monkeypatch):
        monkeypatch.setattr(requests, "post", lambda *a, **k: RespostaFalsa(201, {"slug": "pmg-es-2025-1-ti1"}))
        assert service.criar_equipe("org", "PMG-ES-2025-1-TI1") == "pmg-es-2025-1-ti1"

    def test_envia_os_parametros_esperados_ao_criar(self, service, monkeypatch):
        capturado = {}

        def post_falso(url, headers=None, json=None):
            capturado["url"] = url
            capturado["json"] = json
            return RespostaFalsa(201, {"slug": "equipe"})

        monkeypatch.setattr(requests, "post", post_falso)
        service.criar_equipe("org", "equipe", descricao="TI")

        assert capturado["url"] == "https://api.github.com/orgs/org/teams"
        assert capturado["json"] == {"name": "equipe", "description": "TI", "privacy": "closed"}

    def test_nome_de_equipe_repetido_gera_erro(self, service, monkeypatch):
        dados = {"message": "Validation Failed", "errors": [{"message": "Name must be unique for this org"}]}
        monkeypatch.setattr(requests, "post", lambda *a, **k: RespostaFalsa(422, dados))

        with pytest.raises(GithubServiceError, match="Name must be unique"):
            service.criar_equipe("org", "equipe")

    def test_permissao_da_equipe_usa_a_rota_do_repositorio(self, service, monkeypatch):
        capturado = {}

        def put_falso(url, headers=None, json=None):
            capturado["url"] = url
            capturado["json"] = json
            return RespostaFalsa(204)

        monkeypatch.setattr(requests, "put", put_falso)
        service.definir_permissao_da_equipe("org", "equipe", "repo")

        assert capturado["url"] == "https://api.github.com/orgs/org/teams/equipe/repos/org/repo"
        assert capturado["json"] == {"permission": "admin"}

    def test_falha_ao_conceder_permissao_e_propagada(self, service, monkeypatch):
        monkeypatch.setattr(requests, "put", lambda *a, **k: RespostaFalsa(403, {}))

        with pytest.raises(GithubServiceError, match="Sem permissão"):
            service.definir_permissao_da_equipe("org", "equipe", "repo")

    def test_adicao_de_membro_devolve_o_estado_da_associacao(self, service, monkeypatch):
        monkeypatch.setattr(requests, "put", lambda *a, **k: RespostaFalsa(200, {"state": "active"}))
        assert service.adicionar_membro_na_equipe("org", "equipe", "ana") == "active"

    def test_adicao_de_membro_envia_o_papel(self, service, monkeypatch):
        capturado = {}

        def put_falso(url, headers=None, json=None):
            capturado["url"] = url
            capturado["json"] = json
            return RespostaFalsa(200, {"state": "active"})

        monkeypatch.setattr(requests, "put", put_falso)
        service.adicionar_membro_na_equipe("org", "equipe", "ana")

        assert capturado["url"] == "https://api.github.com/orgs/org/teams/equipe/memberships/ana"
        assert capturado["json"] == {"role": "member"}


class TestUsuarioAutenticado:

    def test_devolve_o_login_do_dono_do_token(self, service, monkeypatch):
        monkeypatch.setattr(requests, "get", lambda *a, **k: RespostaFalsa(200, {"login": "prof-joao"}))
        assert service.obter_usuario_autenticado() == "prof-joao"

    def test_consulta_a_api_uma_unica_vez(self, service, monkeypatch):
        chamadas = []

        def get_falso(*a, **k):
            chamadas.append(1)
            return RespostaFalsa(200, {"login": "prof-joao"})

        monkeypatch.setattr(requests, "get", get_falso)

        for _ in range(5):
            service.obter_usuario_autenticado()

        assert len(chamadas) == 1

    def test_usa_o_endpoint_do_usuario_autenticado(self, service, monkeypatch):
        capturado = {}

        def get_falso(url, headers=None, **k):
            capturado["url"] = url
            return RespostaFalsa(200, {"login": "prof-joao"})

        monkeypatch.setattr(requests, "get", get_falso)
        service.obter_usuario_autenticado()

        assert capturado["url"] == "https://api.github.com/user"

    def test_erro_e_propagado(self, service, monkeypatch):
        monkeypatch.setattr(requests, "get", lambda *a, **k: RespostaFalsa(401, {}))

        with pytest.raises(GithubServiceError, match="Token do GitHub inválido"):
            service.obter_usuario_autenticado()


class TestRemocaoDeMembroDaEquipe:

    def test_usa_a_rota_de_associacao_da_equipe(self, service, monkeypatch):
        capturado = {}

        def delete_falso(url, headers=None, **k):
            capturado["url"] = url
            return RespostaFalsa(204)

        monkeypatch.setattr(requests, "delete", delete_falso)
        service.remover_membro_da_equipe("org", "equipe", "prof-joao")

        assert capturado["url"] == "https://api.github.com/orgs/org/teams/equipe/memberships/prof-joao"

    def test_status_204_conclui_sem_erro(self, service, monkeypatch):
        monkeypatch.setattr(requests, "delete", lambda *a, **k: RespostaFalsa(204))
        assert service.remover_membro_da_equipe("org", "equipe", "prof-joao") is None

    def test_falha_e_propagada(self, service, monkeypatch):
        monkeypatch.setattr(requests, "delete", lambda *a, **k: RespostaFalsa(403, {}))

        with pytest.raises(GithubServiceError, match="Sem permissão"):
            service.remover_membro_da_equipe("org", "equipe", "prof-joao")

    def test_a_remocao_respeita_o_controle_de_ritmo(self, monkeypatch):
        # DELETE cria conteúdo do ponto de vista do limite do GitHub, então é espaçado.
        esperas = []
        monkeypatch.setattr(time, "sleep", lambda s: esperas.append(s))
        monkeypatch.setattr(requests, "delete", lambda *a, **k: RespostaFalsa(204))

        service = GithubService(token="t", intervalo_entre_escritas=0.8)
        service.remover_membro_da_equipe("org", "equipe", "ana")
        service.remover_membro_da_equipe("org", "equipe", "bruno")

        assert len(esperas) == 1
