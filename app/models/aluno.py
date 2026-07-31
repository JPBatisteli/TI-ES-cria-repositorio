from dataclasses import dataclass
import re

# Regra de formação dos nomes de usuário do GitHub: caracteres alfanuméricos e
# hífens, sem hífen no início ou no fim, sem hífens consecutivos, até 39 caracteres.
USERNAME_GITHUB_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")


@dataclass(frozen=True)
class Aluno:
    """
    Representa o aluno que será adicionado como colaborador de um repositório.

    O aluno é identificado pelo seu nome de usuário no GitHub. Os nomes de usuário
    do GitHub não diferenciam maiúsculas de minúsculas, por isso a comparação entre
    alunos usa a forma normalizada.

    Attributes:
        username (str): Nome de usuário do aluno no GitHub.
    """
    username: str

    @classmethod
    def de_texto(cls, texto: str) -> "Aluno":
        """
        Cria um aluno a partir do texto informado pelo professor.

        Remove espaços em volta e o '@' inicial, aceito por ser a forma como o
        usuário costuma ser escrito.

        Args:
            texto (str): Nome de usuário informado (ex: "@joaosilva").

        Returns:
            Aluno: Instância com o nome de usuário limpo.
        """
        return cls(username=texto.strip().lstrip("@").strip())

    @property
    def username_normalizado(self) -> str:
        """Retorna o nome de usuário em minúsculas, usado nas comparações."""
        return self.username.lower()

    @property
    def valido(self) -> bool:
        """Indica se o nome de usuário respeita as regras de formação do GitHub."""
        return bool(USERNAME_GITHUB_REGEX.match(self.username))

    def __str__(self) -> str:
        return self.username
