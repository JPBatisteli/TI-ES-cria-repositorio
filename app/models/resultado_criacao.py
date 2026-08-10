from dataclasses import dataclass, field
from typing import List, Optional

from app.models.novo_repositorio import NovoRepositorio
from app.models.resultado_adicao_aluno import ResultadoAdicaoAluno


@dataclass
class ResultadoCriacao:
    """
    Representa o desfecho de uma solicitação de criação de repositório.

    A criação do repositório e a adição dos alunos são operações independentes:
    o repositório pode ser criado com sucesso ainda que parte dos alunos não seja
    adicionada, e cada aluno tem o seu próprio desfecho registado.

    Attributes:
        novo_repositorio (NovoRepositorio): Solicitação que originou o resultado.
        sucesso (bool): Indica se o repositório foi efetivamente criado.
        url (str): URL do repositório criado, quando a criação for bem-sucedida.
        erros (List[str]): Motivos pelos quais a criação não foi concluída.
        alunos (List[ResultadoAdicaoAluno]): Desfecho da adição de cada aluno.
        equipe (str): Identificador da equipe criada, quando solicitada.
        erro_equipe (str): Motivo pelo qual a equipe não pôde ser criada.
        aviso_equipe (str): Problema que não impediu a criação da equipe, como a
                            remoção do professor não ter sido concluída.
    """
    novo_repositorio: NovoRepositorio
    sucesso: bool = False
    url: str = ""
    erros: List[str] = field(default_factory=list)
    alunos: List[ResultadoAdicaoAluno] = field(default_factory=list)
    equipe: str = ""
    erro_equipe: str = ""
    aviso_equipe: str = ""

    @property
    def total_alunos_adicionados(self) -> int:
        """Retorna a quantidade de alunos que obtiveram acesso ou foram convidados."""
        return sum(1 for resultado in self.alunos if resultado.sucesso)

    @property
    def alunos_com_problema(self) -> List[ResultadoAdicaoAluno]:
        """Retorna os alunos que não puderam ser adicionados ao repositório."""
        return [resultado for resultado in self.alunos if not resultado.sucesso]

    @classmethod
    def criado(cls, novo_repositorio: NovoRepositorio, url: str) -> "ResultadoCriacao":
        """Cria um resultado de sucesso para o repositório informado."""
        return cls(novo_repositorio=novo_repositorio, sucesso=True, url=url)

    @classmethod
    def falha(cls, novo_repositorio: NovoRepositorio, erros: Optional[List[str]] = None) -> "ResultadoCriacao":
        """Cria um resultado de falha com os erros informados."""
        return cls(novo_repositorio=novo_repositorio, sucesso=False, erros=erros or [])

    def __str__(self) -> str:
        """Retorna uma representação legível do resultado da criação."""
        if self.sucesso:
            return f"✅ Repositório '{self.novo_repositorio.nome}' criado com sucesso."
        return "❌ Não foi possível criar o repositório:\n" + "\n".join(f"- {erro}" for erro in self.erros)
