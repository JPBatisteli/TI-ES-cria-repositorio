from dataclasses import dataclass
from enum import Enum

from app.models.aluno import Aluno


class SituacaoAluno(Enum):
    """
    Situações possíveis ao adicionar um aluno como colaborador do repositório.

    Attributes:
        ACESSO_CONCEDIDO: O aluno já é membro da organização e recebeu acesso imediato.
        ADICIONADO_A_EQUIPE: O aluno entrou na equipe, que detém o acesso ao repositório.
        CONVITE_ENVIADO: O GitHub criou um convite, que o aluno precisa aceitar.
        FORA_DA_ORGANIZACAO: O aluno não é membro da organização do campus.
        USERNAME_INVALIDO: O nome de usuário informado não respeita as regras do GitHub.
        ERRO: Falha na comunicação com a API do GitHub.
    """
    ACESSO_CONCEDIDO = "acesso_concedido"
    ADICIONADO_A_EQUIPE = "adicionado_a_equipe"
    CONVITE_ENVIADO = "convite_enviado"
    FORA_DA_ORGANIZACAO = "fora_da_organizacao"
    USERNAME_INVALIDO = "username_invalido"
    ERRO = "erro"


@dataclass
class ResultadoAdicaoAluno:
    """
    Representa o desfecho da tentativa de adicionar um aluno ao repositório.

    Attributes:
        aluno (Aluno): Aluno que se tentou adicionar.
        situacao (SituacaoAluno): Situação resultante da operação.
        detalhe (str): Informação adicional, usada nos casos de erro.
    """
    aluno: Aluno
    situacao: SituacaoAluno
    detalhe: str = ""

    @property
    def sucesso(self) -> bool:
        """Indica se o aluno obteve acesso ao repositório ou foi convidado."""
        return self.situacao in (
            SituacaoAluno.ACESSO_CONCEDIDO,
            SituacaoAluno.ADICIONADO_A_EQUIPE,
            SituacaoAluno.CONVITE_ENVIADO,
        )

    @property
    def descricao(self) -> str:
        """
        Retorna a mensagem exibida ao professor para a situação do aluno.

        Returns:
            str: Mensagem explicando o que aconteceu e, quando necessário, o que fazer.
        """
        if self.situacao == SituacaoAluno.ACESSO_CONCEDIDO:
            return "Acesso de escrita concedido."
        if self.situacao == SituacaoAluno.ADICIONADO_A_EQUIPE:
            return "Adicionado à equipe, que administra o repositório."
        if self.situacao == SituacaoAluno.CONVITE_ENVIADO:
            return "Convite enviado. O aluno precisa aceitá-lo para ter acesso."
        if self.situacao == SituacaoAluno.FORA_DA_ORGANIZACAO:
            return (
                "Não faz parte da organização. Verifique o nome de usuário ou peça "
                "que o aluno seja adicionado à organização antes de tentar novamente."
            )
        if self.situacao == SituacaoAluno.USERNAME_INVALIDO:
            return "Nome de usuário inválido para o GitHub."
        return self.detalhe or "Não foi possível adicionar o aluno."

    def __str__(self) -> str:
        marcador = "✅" if self.sucesso else "❌"
        return f"{marcador} {self.aluno.username}: {self.descricao}"
