import pytest

from app.services import github_service


@pytest.fixture(autouse=True)
def sem_controle_de_ritmo(monkeypatch):
    """
    Desliga o espaçamento entre requisições de escrita durante os testes.

    Sem isso, cada requisição de escrita dos dublês esperaria o intervalo real,
    tornando a suíte lenta sem nada acrescentar. Os testes que verificam o próprio
    controle de ritmo informam o intervalo explicitamente.
    """
    monkeypatch.setattr(github_service, "INTERVALO_MINIMO_ENTRE_ESCRITAS", 0)
