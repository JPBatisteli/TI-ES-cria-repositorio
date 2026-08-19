from typing import Callable, List, Optional

from app.models.aluno import Aluno
from app.models.resultado_adicao_membro import ResultadoAdicaoMembro, SituacaoMembro
from app.services.github_service import GithubService, GithubServiceError

# Estado devolvido pelo GitHub enquanto o convite não é aceito.
ASSOCIACAO_PENDENTE = "pending"


class AdicaoMembrosController:
    """
    Coordena a entrada dos alunos na organização do campus.

    É a etapa anterior à criação dos repositórios: as abas de criação só concedem
    acesso a quem já pertence à organização, e apenas reportam quem está fora dela.
    Este controlador cuida justamente de colocar a turma lá dentro.

    O GitHub não coloca ninguém numa organização sem o seu consentimento. O que a
    aplicação faz é criar o convite; entrar de fato depende de o aluno aceitá-lo.
    """

    def __init__(
            self,
            token: Optional[str] = None,
            ao_aguardar: Optional[Callable[[int, int], None]] = None
    ):
        """
        Args:
            token (Optional[str]): Token pessoal do GitHub. Se não for informado,
                                   é usado o token definido no arquivo .env.
            ao_aguardar (Optional[Callable]): Função chamada quando a aplicação precisa
                                              aguardar por excesso de requisições,
                                              recebendo os segundos e a tentativa.
        """
        self.github_service = GithubService(token=token, ao_aguardar=ao_aguardar)

    def adicionar_membro(self, nome_organizacao: str, aluno: Aluno) -> ResultadoAdicaoMembro:
        """
        Adiciona um aluno à organização, convidando-o quando ainda não for membro.

        Antes de convidar, a aplicação confirma que a conta existe: um nome de usuário
        digitado errado geraria um convite para ninguém, que ficaria pendente para
        sempre na lista da organização.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            aluno (Aluno): Aluno a ser adicionado.

        Returns:
            ResultadoAdicaoMembro: Situação resultante para esse aluno.
        """
        if not aluno.valido:
            return ResultadoAdicaoMembro(aluno=aluno, situacao=SituacaoMembro.USERNAME_INVALIDO)

        try:
            if self.github_service.e_membro(nome_organizacao, aluno.username):
                return ResultadoAdicaoMembro(aluno=aluno, situacao=SituacaoMembro.JA_ERA_MEMBRO)
        except GithubServiceError as erro:
            return ResultadoAdicaoMembro(aluno=aluno, situacao=SituacaoMembro.ERRO, detalhe=str(erro))

        return self._convidar(nome_organizacao, aluno)

    def adicionar_membros(
            self,
            nome_organizacao: str,
            alunos: List[Aluno],
            ao_concluir_cada: Optional[Callable[[int, ResultadoAdicaoMembro], None]] = None
    ) -> List[ResultadoAdicaoMembro]:
        """
        Adiciona vários alunos à organização, em sequência.

        A lista de membros é carregada uma única vez e consultada em memória: só os
        alunos que ainda não pertencem à organização custam requisições. Cada aluno é
        independente — a falha de um não interrompe os seguintes.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            alunos (List[Aluno]): Alunos lidos do arquivo.
            ao_concluir_cada (Optional[Callable]): Função chamada após cada aluno,
                                                   recebendo o índice e o resultado.
                                                   Permite acompanhar o progresso.

        Returns:
            List[ResultadoAdicaoMembro]: Resultado de cada aluno, na ordem original.
        """
        if not alunos:
            return []

        try:
            membros = {
                nome.lower()
                for nome in self.github_service.listar_membros(nome_organizacao, papel="all")
            }
        except GithubServiceError as erro:
            # Sem a lista, cada aluno seria consultado individualmente; é mais honesto
            # informar a falha do que multiplicá-la por toda a turma.
            return [
                ResultadoAdicaoMembro(aluno=aluno, situacao=SituacaoMembro.ERRO, detalhe=str(erro))
                for aluno in alunos
            ]

        resultados = []

        for indice, aluno in enumerate(alunos):
            resultado = self._adicionar_conhecendo_os_membros(nome_organizacao, aluno, membros)
            resultados.append(resultado)

            if ao_concluir_cada:
                ao_concluir_cada(indice, resultado)

        return resultados

    def _adicionar_conhecendo_os_membros(
            self,
            nome_organizacao: str,
            aluno: Aluno,
            membros: set
    ) -> ResultadoAdicaoMembro:
        """
        Adiciona um aluno aproveitando a lista de membros já carregada.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            aluno (Aluno): Aluno a ser adicionado.
            membros (set): Nomes de usuário dos membros da organização, em minúsculas.

        Returns:
            ResultadoAdicaoMembro: Situação resultante para esse aluno.
        """
        if not aluno.valido:
            return ResultadoAdicaoMembro(aluno=aluno, situacao=SituacaoMembro.USERNAME_INVALIDO)

        if aluno.username_normalizado in membros:
            return ResultadoAdicaoMembro(aluno=aluno, situacao=SituacaoMembro.JA_ERA_MEMBRO)

        return self._convidar(nome_organizacao, aluno)

    def _convidar(self, nome_organizacao: str, aluno: Aluno) -> ResultadoAdicaoMembro:
        """
        Confirma que a conta existe e envia o convite para a organização.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            aluno (Aluno): Aluno já sabidamente fora da organização.

        Returns:
            ResultadoAdicaoMembro: Situação resultante para esse aluno.
        """
        try:
            if not self.github_service.usuario_existe(aluno.username):
                return ResultadoAdicaoMembro(aluno=aluno, situacao=SituacaoMembro.CONTA_INEXISTENTE)

            estado = self.github_service.adicionar_membro_na_organizacao(
                nome_organizacao=nome_organizacao,
                username=aluno.username
            )
        except GithubServiceError as erro:
            return ResultadoAdicaoMembro(aluno=aluno, situacao=SituacaoMembro.ERRO, detalhe=str(erro))

        situacao = (
            SituacaoMembro.CONVITE_ENVIADO if estado == ASSOCIACAO_PENDENTE
            else SituacaoMembro.ENTROU
        )
        return ResultadoAdicaoMembro(aluno=aluno, situacao=situacao)
