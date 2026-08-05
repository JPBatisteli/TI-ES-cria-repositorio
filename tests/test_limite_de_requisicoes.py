import time

import pytest
import requests

from app.services import github_service
from app.services.github_service import (
    SEGUNDOS_DE_ESPERA_PADRAO,
    GithubService,
    GithubServiceError,
    LimiteDeRequisicoesError,
)


# Capturado na importação, antes que o fixture da conftest zere o intervalo para
# manter a suíte rápida. Os testes que documentam o valor configurado usam esta cópia.
INTERVALO_CONFIGURADO = github_service.INTERVALO_MINIMO_ENTRE_ESCRITAS


class RespostaFalsa:
    """Dublê de requests.Response, com cabeçalhos controláveis."""

    def __init__(self, status_code: int, dados=None, texto: str = "", headers=None):
        self.status_code = status_code
        self._dados = dados
        self.text = texto
        self.headers = headers or {}

    def json(self):
        if self._dados is None:
            raise ValueError("Resposta sem corpo JSON.")
        return self._dados


def resposta_de_limite(**headers) -> RespostaFalsa:
    """Resposta 403 típica de excesso de requisições."""
    return RespostaFalsa(
        403,
        {"message": "You have exceeded a secondary rate limit. Please wait a few minutes."},
        headers=headers
    )


@pytest.fixture
def sem_espera(monkeypatch):
    """Substitui a espera real, registrando quantos segundos teriam sido aguardados."""
    esperas = []
    monkeypatch.setattr(time, "sleep", lambda segundos: esperas.append(segundos))
    return esperas


class TestDeteccaoDoLimite:

    @pytest.mark.parametrize("resposta", [
        resposta_de_limite(),
        resposta_de_limite(**{"Retry-After": "12"}),
        RespostaFalsa(403, {}, headers={"x-ratelimit-remaining": "0"}),
        RespostaFalsa(429, {"message": "Rate limit exceeded"}),
        RespostaFalsa(403, {"message": "You have triggered an abuse detection mechanism"}),
    ])
    def test_reconhece_as_respostas_de_limite(self, resposta):
        assert GithubService._e_limite_de_requisicoes(resposta) is True

    @pytest.mark.parametrize("resposta", [
        RespostaFalsa(403, {"message": "Must have admin rights to Repository."}),
        RespostaFalsa(401, {"message": "Bad credentials"}),
        RespostaFalsa(404, {}),
        RespostaFalsa(200, {}),
        RespostaFalsa(403, None, texto="erro sem json"),
    ])
    def test_nao_confunde_com_outros_erros(self, resposta):
        assert GithubService._e_limite_de_requisicoes(resposta) is False


class TestTempoDeEspera:

    def test_respeita_o_cabecalho_retry_after(self):
        assert GithubService._segundos_de_espera(resposta_de_limite(**{"Retry-After": "12"})) == 12

    def test_usa_o_ratelimit_reset_quando_nao_ha_retry_after(self):
        reset = int(time.time()) + 45
        resposta = resposta_de_limite(**{"x-ratelimit-reset": str(reset)})

        assert 40 <= GithubService._segundos_de_espera(resposta) <= 45

    def test_sem_cabecalhos_adota_a_espera_padrao(self):
        assert GithubService._segundos_de_espera(resposta_de_limite()) == SEGUNDOS_DE_ESPERA_PADRAO
        assert SEGUNDOS_DE_ESPERA_PADRAO == 30

    def test_ignora_reset_no_passado(self):
        resposta = resposta_de_limite(**{"x-ratelimit-reset": str(int(time.time()) - 100)})
        assert GithubService._segundos_de_espera(resposta) == SEGUNDOS_DE_ESPERA_PADRAO


class TestRepeticaoAutomatica:

    def test_repete_a_requisicao_apos_a_espera(self, monkeypatch, sem_espera):
        respostas = [resposta_de_limite(), RespostaFalsa(201, {"html_url": "u"})]
        monkeypatch.setattr(requests, "post", lambda *a, **k: respostas.pop(0))

        dados = GithubService(token="t").criar_repositorio("org", "repo")

        assert dados == {"html_url": "u"}
        assert sem_espera == [SEGUNDOS_DE_ESPERA_PADRAO]

    def test_avisa_o_usuario_antes_de_cada_espera(self, monkeypatch, sem_espera):
        respostas = [
            resposta_de_limite(**{"Retry-After": "5"}),
            resposta_de_limite(**{"Retry-After": "5"}),
        ]
        monkeypatch.setattr(requests, "post", lambda *a, **k: respostas.pop(0) if respostas else RespostaFalsa(201, {}))

        avisos = []
        service = GithubService(token="t", ao_aguardar=lambda s, t: avisos.append((s, t)))
        service.criar_repositorio("org", "repo")

        assert avisos == [(5, 1), (5, 2)]
        assert sem_espera == [5, 5]

    def test_desiste_apos_o_maximo_de_tentativas(self, monkeypatch, sem_espera):
        chamadas = []

        def post_falso(*a, **k):
            chamadas.append(1)
            return resposta_de_limite()

        monkeypatch.setattr(requests, "post", post_falso)

        with pytest.raises(LimiteDeRequisicoesError, match="excesso de requisições"):
            GithubService(token="t").criar_repositorio("org", "repo")

        assert len(chamadas) == github_service.MAXIMO_DE_TENTATIVAS
        assert len(sem_espera) == github_service.MAXIMO_DE_TENTATIVAS - 1

    def test_nao_repete_erros_que_nao_sao_de_limite(self, monkeypatch, sem_espera):
        chamadas = []

        def post_falso(*a, **k):
            chamadas.append(1)
            return RespostaFalsa(403, {"message": "Must have admin rights to Repository."})

        monkeypatch.setattr(requests, "post", post_falso)

        with pytest.raises(GithubServiceError, match="Sem permissão"):
            GithubService(token="t").criar_repositorio("org", "repo")

        assert len(chamadas) == 1
        assert sem_espera == []

    def test_a_espera_vale_para_as_consultas_tambem(self, monkeypatch, sem_espera):
        respostas = [resposta_de_limite(), RespostaFalsa(200, {})]
        monkeypatch.setattr(requests, "get", lambda *a, **k: respostas.pop(0))

        assert GithubService(token="t").repositorio_existe("org", "repo") is True
        assert sem_espera == [SEGUNDOS_DE_ESPERA_PADRAO]


class TestMensagemAoProfessor:

    def test_limite_nao_e_mais_reportado_como_falta_de_permissao(self, monkeypatch, sem_espera):
        monkeypatch.setattr(requests, "post", lambda *a, **k: resposta_de_limite())

        with pytest.raises(GithubServiceError) as excecao:
            GithubService(token="t").criar_repositorio("org", "repo")

        mensagem = str(excecao.value)
        assert "Não é problema de permissão" in mensagem
        assert "escopo 'repo'" not in mensagem

    def test_erro_de_limite_e_um_erro_de_servico(self):
        # Garante que o controller, que captura GithubServiceError, continua tratando o caso.
        assert issubclass(LimiteDeRequisicoesError, GithubServiceError)


class TestControleDeRitmo:
    """O espaçamento entre escritas evita o bloqueio em vez de reagir a ele."""

    @staticmethod
    def service_com_ritmo(intervalo=0.8) -> GithubService:
        return GithubService(token="t", intervalo_entre_escritas=intervalo)

    def test_escritas_seguidas_sao_espacadas(self, monkeypatch, sem_espera):
        monkeypatch.setattr(requests, "post", lambda *a, **k: RespostaFalsa(201, {}))
        service = self.service_com_ritmo()

        service.criar_repositorio("org", "repo-1")
        service.criar_repositorio("org", "repo-2")
        service.criar_repositorio("org", "repo-3")

        # A primeira escrita não espera; as seguintes respeitam o intervalo.
        assert len(sem_espera) == 2
        assert all(0 < segundos <= 0.8 for segundos in sem_espera)

    def test_consultas_nao_sao_espacadas(self, monkeypatch, sem_espera):
        monkeypatch.setattr(requests, "get", lambda *a, **k: RespostaFalsa(200, {}))
        service = self.service_com_ritmo()

        for _ in range(5):
            service.repositorio_existe("org", "repo")

        assert sem_espera == []

    def test_intervalo_zero_desliga_o_controle(self, monkeypatch, sem_espera):
        monkeypatch.setattr(requests, "post", lambda *a, **k: RespostaFalsa(201, {}))
        service = self.service_com_ritmo(intervalo=0)

        service.criar_repositorio("org", "repo-1")
        service.criar_repositorio("org", "repo-2")

        assert sem_espera == []

    def test_o_ritmo_vale_para_todas_as_operacoes_de_escrita(self, monkeypatch, sem_espera):
        monkeypatch.setattr(requests, "post", lambda *a, **k: RespostaFalsa(201, {"slug": "s"}))
        monkeypatch.setattr(requests, "put", lambda *a, **k: RespostaFalsa(204))
        service = self.service_com_ritmo()

        service.criar_equipe("org", "equipe")
        service.definir_permissao_da_equipe("org", "equipe", "repo")
        service.adicionar_colaborador("org", "repo", "ana")

        assert len(sem_espera) == 2

    def test_o_intervalo_padrao_respeita_o_limite_do_github(self):
        # 80 escritas por minuto é o teto; o intervalo adotado mantém margem.
        escritas_por_minuto = 60 / INTERVALO_CONFIGURADO
        assert escritas_por_minuto < 80

    def test_o_pior_caso_de_turma_fica_abaixo_do_teto(self):
        # 10 grupos de 6 alunos: 3 escritas por grupo (repositório, equipe, permissão)
        # mais 1 por aluno. Sem espaçamento, as 90 escritas estourariam o teto de 80/min.
        escritas = 3 * 10 + 60
        duracao = (escritas - 1) * INTERVALO_CONFIGURADO

        assert escritas == 90
        assert duracao > 60
