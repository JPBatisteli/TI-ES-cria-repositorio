import pytest
import requests

from app.controllers.criacao_repositorio_controller import CriacaoRepositorioController
from app.models.arquivo_lote import ArquivoLote
from app.models.campus import CAMPI, obter_campus
from app.models.disciplina import Disciplina
from app.models.novo_repositorio import NovoRepositorio
from app.models.template import Template
from app.services.github_service import GithubService, GithubServiceError

from test_criacao_de_equipe import GithubServiceFalso, criar_controller
from test_github_service import RespostaFalsa


class TestTemplateDoCampus:

    def test_cada_campus_tem_o_modelo_da_propria_organizacao(self):
        for campus in CAMPI.values():
            assert campus.template is not None
            assert campus.template.owner == campus.organizacao
            assert campus.template.repositorio == "TI-ES-GenericTemplate"

    @pytest.mark.parametrize("nome_campus, esperado", [
        ("Coração Eucarístico", "ICEI-PUC-Minas-PMGES-TI/TI-ES-GenericTemplate"),
        ("Lourdes", "ICEI-PUC-Minas-PPLES-TI/TI-ES-GenericTemplate"),
    ])
    def test_identificador_completo_do_modelo(self, nome_campus, esperado):
        assert obter_campus(nome_campus).template.nome_completo == esperado

    def test_url_do_modelo(self):
        template = obter_campus("Lourdes").template
        assert template.url == "https://github.com/ICEI-PUC-Minas-PPLES-TI/TI-ES-GenericTemplate"

    def test_solicitacao_adota_o_modelo_do_campus(self):
        solicitacao = NovoRepositorio(
            campus=obter_campus("Coração Eucarístico"),
            disciplina=Disciplina.TI1,
            codigo_disciplina="2401100",
            nome_projeto="Adota Pet"
        )

        assert solicitacao.usa_template is True
        assert solicitacao.template.owner == "ICEI-PUC-Minas-PMGES-TI"

    def test_campus_sem_modelo_nao_usa_template(self):
        from app.models.campus import Campus

        solicitacao = NovoRepositorio(
            campus=Campus(sigla="xxx", nome="Sem Modelo", organizacao="Org"),
            disciplina=Disciplina.TI1,
            codigo_disciplina="2401100",
            nome_projeto="Adota Pet"
        )

        assert solicitacao.usa_template is False
        assert solicitacao.template is None


class TestCriacaoAPartirDoModelo:

    @staticmethod
    def criar_solicitacao(campus="Coração Eucarístico", disciplina=Disciplina.TI2) -> NovoRepositorio:
        # TI2 não tem modelo próprio, portanto exercita o modelo padrão do campus.
        return NovoRepositorio(
            campus=obter_campus(campus),
            disciplina=disciplina,
            codigo_disciplina="8183100",
            nome_projeto="Adota Pet",
            criar_equipe=False
        )

    def test_usa_o_modelo_da_organizacao_do_campus(self):
        service = GithubServiceFalso()
        criar_controller(service).criar_repositorio(self.criar_solicitacao())

        assert service.templates_usados == ["ICEI-PUC-Minas-PMGES-TI/TI-ES-GenericTemplate"]

    def test_cada_campus_usa_o_proprio_modelo(self):
        service = GithubServiceFalso()
        criar_controller(service).criar_repositorio(self.criar_solicitacao("Lourdes"))

        assert service.templates_usados == ["ICEI-PUC-Minas-PPLES-TI/TI-ES-GenericTemplate"]

    def test_repositorio_e_criado_normalmente(self):
        service = GithubServiceFalso()
        resultado = criar_controller(service).criar_repositorio(self.criar_solicitacao())

        assert resultado.sucesso is True
        assert resultado.url


class TestServicoDeGeracaoPorModelo:

    @pytest.fixture
    def service(self) -> GithubService:
        return GithubService(token="token-de-teste")

    def test_envia_os_parametros_esperados(self, service, monkeypatch):
        capturado = {}

        def post_falso(url, headers=None, json=None):
            capturado["url"] = url
            capturado["json"] = json
            return RespostaFalsa(201, {"html_url": "u"})

        monkeypatch.setattr(requests, "post", post_falso)

        service.criar_repositorio_por_template(
            "org-modelo", "TI-ES-GenericTemplate", "org-destino", "repo",
            descricao="TI", privado=True
        )

        assert capturado["url"] == "https://api.github.com/repos/org-modelo/TI-ES-GenericTemplate/generate"
        assert capturado["json"] == {
            "owner": "org-destino",
            "name": "repo",
            "description": "TI",
            "private": True,
            "include_all_branches": False,
        }

    def test_falha_e_propagada(self, service, monkeypatch):
        monkeypatch.setattr(requests, "post", lambda *a, **k: RespostaFalsa(404, {}))

        with pytest.raises(GithubServiceError, match="não encontrado"):
            service.criar_repositorio_por_template("o", "t", "org", "repo")

    def test_repositorio_e_reconhecido_como_modelo(self, service, monkeypatch):
        monkeypatch.setattr(requests, "get", lambda *a, **k: RespostaFalsa(200, {"is_template": True}))
        assert service.e_template("org", "modelo") is True

    def test_repositorio_comum_nao_e_modelo(self, service, monkeypatch):
        monkeypatch.setattr(requests, "get", lambda *a, **k: RespostaFalsa(200, {"is_template": False}))
        assert service.e_template("org", "comum") is False

    def test_repositorio_inexistente_nao_e_modelo(self, service, monkeypatch):
        monkeypatch.setattr(requests, "get", lambda *a, **k: RespostaFalsa(404, {}))
        assert service.e_template("org", "sumido") is False


class TestVerificacaoDoModeloNoLote:

    ARQUIVO = """Repositorio: Projeto A
Grupo: Grupo A
Membros: ana

Repositorio: Projeto B
Grupo: Grupo B
Membros: bruno
"""

    @staticmethod
    def verificar(template_valido: bool):
        from test_verificacao_lote import GithubServiceFalso as ServiceDeVerificacao

        service = ServiceDeVerificacao(membros=["ana", "bruno"], template_valido=template_valido)
        controller = CriacaoRepositorioController(token="t")
        controller.github_service = service
        solicitacoes = ArquivoLote.de_texto(TestVerificacaoDoModeloNoLote.ARQUIVO).montar_solicitacoes(
            obter_campus("Coração Eucarístico"), Disciplina.TI1, "2401100"
        )
        return controller.verificar_lote(solicitacoes), service

    def test_modelo_valido_libera_a_criacao(self):
        verificacao, _ = self.verificar(template_valido=True)

        assert verificacao.erro_template == ""
        assert verificacao.pode_criar is True

    def test_modelo_invalido_bloqueia_todo_o_lote(self):
        verificacao, _ = self.verificar(template_valido=False)

        assert "não está marcado como template" in verificacao.erro_template
        assert verificacao.pode_criar is False

    def test_o_modelo_e_consultado_uma_unica_vez_por_lote(self):
        _, service = self.verificar(template_valido=True)

        assert service.consultas_de_template == ["ICEI-PUC-Minas-PMGES-TI/ti1-es-template-repository"]


class TestPadraoFixoDeCriacao:
    """Visibilidade e origem do conteúdo deixaram de ser escolha do professor."""

    @staticmethod
    def solicitacao(campus="Coração Eucarístico") -> NovoRepositorio:
        return NovoRepositorio(
            campus=obter_campus(campus),
            disciplina=Disciplina.TI1,
            codigo_disciplina="2401100",
            nome_projeto="Adota Pet",
            criar_equipe=False
        )

    def test_repositorio_nasce_privado_sem_precisar_informar(self):
        assert self.solicitacao().privado is True

    def test_a_opcao_de_readme_inicial_deixou_de_existir(self):
        assert not hasattr(self.solicitacao(), "inicializar_readme")

    def test_a_criacao_envia_private_verdadeiro(self):
        capturado = {}

        class ServiceQueCaptura(GithubServiceFalso):
            def criar_repositorio_por_template(self, template_owner, template_repositorio,
                                               nome_organizacao, nome_repositorio, descricao="",
                                               privado=False, incluir_todas_as_branches=False):
                capturado["privado"] = privado
                return super().criar_repositorio_por_template(
                    template_owner, template_repositorio, nome_organizacao,
                    nome_repositorio, descricao, privado, incluir_todas_as_branches
                )

        service = ServiceQueCaptura()
        criar_controller(service).criar_repositorio(self.solicitacao())

        assert capturado["privado"] is True


# Espelho do cadastro, escrito de forma independente para que uma alteração acidental
# em CAMPI seja detectada. Disciplinas ausentes usam o modelo padrão do campus.
MODELOS_PROPRIOS = {
    Disciplina.TI1: "ti1-es-template-repository",
    Disciplina.TI3: "ti3-es-template-repository",
}
MODELO_PADRAO = "TI-ES-GenericTemplate"

ORGANIZACAO_DO_CAMPUS = {
    "Coração Eucarístico": "ICEI-PUC-Minas-PMGES-TI",
    "Lourdes": "ICEI-PUC-Minas-PPLES-TI",
}


class TestModeloEspecificoDaDisciplina:
    """Algumas disciplinas adotam modelo próprio; as demais seguem o padrão do campus."""

    @staticmethod
    def solicitacao(campus: str, disciplina: Disciplina) -> NovoRepositorio:
        return NovoRepositorio(
            campus=obter_campus(campus),
            disciplina=disciplina,
            codigo_disciplina="0427100",
            nome_projeto="Adota Pet",
            criar_equipe=False
        )

    @pytest.mark.parametrize("campus", list(ORGANIZACAO_DO_CAMPUS))
    @pytest.mark.parametrize("disciplina", list(Disciplina))
    def test_modelo_resolvido_para_cada_disciplina(self, campus, disciplina):
        esperado = MODELOS_PROPRIOS.get(disciplina, MODELO_PADRAO)
        template = self.solicitacao(campus, disciplina).template

        assert template.nome_completo == f"{ORGANIZACAO_DO_CAMPUS[campus]}/{esperado}"

    @pytest.mark.parametrize("disciplina", list(MODELOS_PROPRIOS))
    def test_modelo_proprio_fica_na_organizacao_do_campus(self, disciplina):
        for nome, campus in CAMPI.items():
            assert campus.template_para(disciplina).owner == campus.organizacao, nome

    def test_disciplina_sem_modelo_proprio_recai_no_padrao(self):
        campus = obter_campus("Lourdes")
        assert campus.template_para(Disciplina.TI6) == campus.template

    def test_sem_disciplina_informada_usa_o_padrao(self):
        campus = obter_campus("Lourdes")
        assert campus.template_para(None) == campus.template

    @pytest.mark.parametrize("disciplina", list(Disciplina))
    def test_a_criacao_usa_o_modelo_resolvido(self, disciplina):
        esperado = MODELOS_PROPRIOS.get(disciplina, MODELO_PADRAO)
        service = GithubServiceFalso()

        criar_controller(service).criar_repositorio(
            self.solicitacao("Coração Eucarístico", disciplina)
        )

        assert service.templates_usados == [f"ICEI-PUC-Minas-PMGES-TI/{esperado}"]


