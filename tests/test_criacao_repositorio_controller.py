import pytest

from app.controllers.criacao_repositorio_controller import CriacaoRepositorioController
from app.models.campus import obter_campus
from app.models.disciplina import Disciplina
from app.models.novo_repositorio import NovoRepositorio
from app.models.periodo_letivo import PeriodoLetivo
from app.services.github_service import GithubServiceError, RepositorioJaExisteError


class GithubServiceFalso:
    """Dublê do GithubService, usado para testar o controller sem acessar a API."""

    def __init__(self, existe: bool = False, erro: str = "", erro_duplicidade: bool = False):
        self.existe = existe
        self.erro = erro
        self.erro_duplicidade = erro_duplicidade
        self.chamadas = []

    def repositorio_existe(self, nome_organizacao, nome_repositorio):
        self.chamadas.append(("existe", nome_organizacao, nome_repositorio))
        return self.existe

    def criar_repositorio(self, nome_organizacao, nome_repositorio, descricao="",
                          privado=False, inicializar_readme=True):
        self.chamadas.append(("criar", nome_organizacao, nome_repositorio))
        if self.erro_duplicidade:
            raise RepositorioJaExisteError("name already exists on this account")
        if self.erro:
            raise GithubServiceError(self.erro)
        return {"html_url": f"https://github.com/{nome_organizacao}/{nome_repositorio}"}

    def criar_repositorio_por_template(self, template_owner, template_repositorio, nome_organizacao,
                                       nome_repositorio, descricao="", privado=False,
                                       incluir_todas_as_branches=False):
        self.chamadas.append(("template", f"{template_owner}/{template_repositorio}"))
        return self.criar_repositorio(nome_organizacao, nome_repositorio, descricao, privado)


@pytest.fixture
def solicitacao() -> NovoRepositorio:
    return NovoRepositorio(
        campus=obter_campus("Lourdes"),
        disciplina=Disciplina.TI4,
        codigo_disciplina="1247100",
        nome_projeto="Donatio ONG",
        ano=2025,
        semestre=1,
        periodo_letivo_atual=PeriodoLetivo(2025, 1)
    )


def criar_controller(service: GithubServiceFalso) -> CriacaoRepositorioController:
    controller = CriacaoRepositorioController(token="token-de-teste")
    controller.github_service = service
    return controller


def test_cria_o_repositorio_na_organizacao_do_campus(solicitacao):
    service = GithubServiceFalso()
    resultado = criar_controller(service).criar_repositorio(solicitacao)

    assert resultado.sucesso is True
    assert resultado.url == (
        "https://github.com/ICEI-PUC-Minas-PPLES-TI/plf-es-2025-1-ti4-1247100-donatio-ong"
    )
    assert ("criar", "ICEI-PUC-Minas-PPLES-TI", "plf-es-2025-1-ti4-1247100-donatio-ong") in service.chamadas


def test_nao_cria_repositorio_ja_existente(solicitacao):
    service = GithubServiceFalso(existe=True)
    resultado = criar_controller(service).criar_repositorio(solicitacao)

    assert resultado.sucesso is False
    assert resultado.erros == [
        "Já existe um repositório chamado 'plf-es-2025-1-ti4-1247100-donatio-ong' na "
        "organização ICEI-PUC-Minas-PPLES-TI. Altere o nome do repositório ou verifique "
        "se ele já foi criado em ICEI-PUC-Minas-PPLES-TI/plf-es-2025-1-ti4-1247100-donatio-ong."
    ]
    assert all(chamada[0] != "criar" for chamada in service.chamadas)


def test_duplicidade_detectada_apenas_pela_api_gera_a_mesma_mensagem(solicitacao):
    """
    Cobre o caso do repositório existente que não é visível para o token: a
    verificação prévia não o encontra e a recusa vem da API, na criação.
    """
    service_visivel = GithubServiceFalso(existe=True)
    resultado_visivel = criar_controller(service_visivel).criar_repositorio(solicitacao)

    service_invisivel = GithubServiceFalso(existe=False, erro_duplicidade=True)
    resultado_invisivel = criar_controller(service_invisivel).criar_repositorio(solicitacao)

    assert resultado_invisivel.sucesso is False
    assert resultado_invisivel.erros == resultado_visivel.erros
    assert any(chamada[0] == "criar" for chamada in service_invisivel.chamadas)


def test_nao_chama_a_api_quando_os_dados_sao_invalidos(solicitacao):
    solicitacao.codigo_disciplina = "abc"
    service = GithubServiceFalso()
    resultado = criar_controller(service).criar_repositorio(solicitacao)

    assert resultado.sucesso is False
    assert service.chamadas == []


def test_erro_da_api_e_devolvido_como_falha(solicitacao):
    service = GithubServiceFalso(erro="Token do GitHub inválido ou expirado.")
    resultado = criar_controller(service).criar_repositorio(solicitacao)

    assert resultado.sucesso is False
    assert resultado.erros == ["Token do GitHub inválido ou expirado."]
