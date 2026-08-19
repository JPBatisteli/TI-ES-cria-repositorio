from dataclasses import dataclass
from enum import Enum

from app.models.aluno import Aluno


class SituacaoMembro(Enum):
    """
    Situações possíveis ao adicionar um aluno à organização.

    Attributes:
        CONVITE_ENVIADO: O GitHub criou o convite, que o aluno precisa aceitar.
        JA_ERA_MEMBRO: O aluno já pertencia à organização; nada foi alterado.
        ENTROU: O aluno passou a constar como membro ativo, sem convite pendente.
        USERNAME_INVALIDO: O nome de usuário não respeita as regras do GitHub.
        CONTA_INEXISTENTE: Não existe conta com esse nome de usuário.
        ERRO: Falha na comunicação com a API do GitHub.
    """
    CONVITE_ENVIADO = "convite_enviado"
    JA_ERA_MEMBRO = "ja_era_membro"
    ENTROU = "entrou"
    USERNAME_INVALIDO = "username_invalido"
    CONTA_INEXISTENTE = "conta_inexistente"
    ERRO = "erro"


@dataclass
class ResultadoAdicaoMembro:
    """
    Representa o desfecho da tentativa de adicionar um aluno à organização.

    Attributes:
        aluno (Aluno): Aluno que se tentou adicionar.
        situacao (SituacaoMembro): Situação resultante da operação.
        detalhe (str): Informação adicional, usada nos casos de erro.
    """
    aluno: Aluno
    situacao: SituacaoMembro
    detalhe: str = ""

    @property
    def sucesso(self) -> bool:
        """
        Indica que o aluno está na organização ou foi convidado a entrar.

        Quem já era membro conta como sucesso: o estado desejado é o mesmo, e reenviar
        a lista da turma não deve parecer ter falhado.
        """
        return self.situacao in (
            SituacaoMembro.CONVITE_ENVIADO,
            SituacaoMembro.JA_ERA_MEMBRO,
            SituacaoMembro.ENTROU,
        )

    @property
    def convite_pendente(self) -> bool:
        """Indica que o aluno ainda precisa aceitar o convite."""
        return self.situacao == SituacaoMembro.CONVITE_ENVIADO

    @property
    def descricao(self) -> str:
        """
        Retorna a mensagem exibida ao professor para a situação do aluno.

        Returns:
            str: Mensagem explicando o que aconteceu e, quando necessário, o que fazer.
        """
        if self.situacao == SituacaoMembro.CONVITE_ENVIADO:
            return "Convite enviado. O aluno precisa aceitá-lo para entrar na organização."
        if self.situacao == SituacaoMembro.JA_ERA_MEMBRO:
            return "Já era membro da organização. Nada foi alterado."
        if self.situacao == SituacaoMembro.ENTROU:
            return "Entrou na organização."
        if self.situacao == SituacaoMembro.USERNAME_INVALIDO:
            return "Nome de usuário inválido para o GitHub."
        if self.situacao == SituacaoMembro.CONTA_INEXISTENTE:
            return "Não existe conta com esse nome de usuário no GitHub. Confira a grafia."
        return self.detalhe or "Não foi possível adicionar o aluno à organização."

    def __str__(self) -> str:
        marcador = "✅" if self.sucesso else "❌"
        return f"{marcador} {self.aluno.username}: {self.descricao}"
