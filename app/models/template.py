from dataclasses import dataclass


@dataclass(frozen=True)
class Template:
    """
    Representa o repositório-modelo usado como base para os repositórios das equipes.

    O repositório de origem precisa estar marcado como template no GitHub
    (`is_template: true`), caso contrário a API recusa a geração.

    Attributes:
        owner (str): Organização ou usuário dono do repositório-modelo.
        repositorio (str): Nome do repositório-modelo.
    """
    owner: str
    repositorio: str

    @property
    def nome_completo(self) -> str:
        """Retorna o identificador no formato 'owner/repositorio'."""
        return f"{self.owner}/{self.repositorio}"

    @property
    def url(self) -> str:
        """Retorna a URL do repositório-modelo no GitHub."""
        return f"https://github.com/{self.nome_completo}"

    def __str__(self) -> str:
        return self.nome_completo
