from dataclasses import dataclass, field
from typing import List

from app.models.novo_repositorio import NovoRepositorio


@dataclass
class VerificacaoGrupo:
    """
    Reúne o resultado da verificação prévia de um grupo do arquivo de lote.

    A verificação acontece antes de qualquer criação e apenas consulta a API do
    GitHub: nada é criado, alterado ou convidado nesta etapa.

    Attributes:
        solicitacao (NovoRepositorio): Solicitação montada a partir do grupo.
        repositorio_disponivel (bool): Indica que ainda não existe repositório com esse nome.
        equipe_disponivel (bool): Indica que ainda não existe equipe com esse nome.
        alunos_encontrados (List[str]): Alunos que pertencem à organização.
        alunos_fora_da_organizacao (List[str]): Contas que existem, mas não são membros.
        alunos_inexistentes (List[str]): Nomes de usuário que não existem no GitHub.
        alunos_invalidos (List[str]): Nomes de usuário fora das regras de formação.
        erro (str): Falha de comunicação que impediu a verificação deste grupo.
    """
    solicitacao: NovoRepositorio
    repositorio_disponivel: bool = True
    equipe_disponivel: bool = True
    alunos_encontrados: List[str] = field(default_factory=list)
    alunos_fora_da_organizacao: List[str] = field(default_factory=list)
    alunos_inexistentes: List[str] = field(default_factory=list)
    alunos_invalidos: List[str] = field(default_factory=list)
    erro: str = ""

    @property
    def impedimentos(self) -> List[str]:
        """
        Retorna os problemas que impedem a criação deste grupo.

        Returns:
            List[str]: Mensagens descrevendo cada impedimento encontrado.
        """
        impedimentos = []

        if self.erro:
            impedimentos.append(self.erro)
        if not self.repositorio_disponivel:
            impedimentos.append(f"O repositório '{self.solicitacao.nome}' já existe na organização.")
        if not self.equipe_disponivel:
            impedimentos.append(f"A equipe '{self.solicitacao.nome_equipe}' já existe na organização.")
        if self.alunos_invalidos:
            impedimentos.append(
                f"Nome de usuário inválido: {', '.join(self.alunos_invalidos)}."
            )
        if self.alunos_inexistentes:
            impedimentos.append(
                f"Não existe no GitHub: {', '.join(self.alunos_inexistentes)}."
            )
        if self.alunos_fora_da_organizacao:
            impedimentos.append(
                f"Fora da organização: {', '.join(self.alunos_fora_da_organizacao)}."
            )

        return impedimentos

    @property
    def apto(self) -> bool:
        """Indica que o grupo pode ser criado sem problemas conhecidos."""
        return not self.impedimentos

    @property
    def total_alunos(self) -> int:
        """Retorna a quantidade de alunos informados para o grupo."""
        return len(self.solicitacao.alunos_unicos)


@dataclass
class VerificacaoLote:
    """
    Reúne o resultado da verificação de todos os grupos do arquivo.

    Attributes:
        grupos (List[VerificacaoGrupo]): Verificação de cada grupo, na ordem do arquivo.
    """
    grupos: List[VerificacaoGrupo] = field(default_factory=list)

    @property
    def apto(self) -> bool:
        """Indica que todos os grupos podem ser criados."""
        return bool(self.grupos) and all(grupo.apto for grupo in self.grupos)

    @property
    def grupos_com_impedimento(self) -> List[VerificacaoGrupo]:
        """Retorna os grupos que possuem ao menos um impedimento."""
        return [grupo for grupo in self.grupos if not grupo.apto]

    @property
    def total_alunos_encontrados(self) -> int:
        """Retorna a quantidade de alunos localizados na organização."""
        return sum(len(grupo.alunos_encontrados) for grupo in self.grupos)

    @property
    def total_alunos(self) -> int:
        """Retorna a quantidade de alunos informados no arquivo."""
        return sum(grupo.total_alunos for grupo in self.grupos)

    @property
    def nenhum_aluno_encontrado(self) -> bool:
        """
        Indica que nenhum aluno do arquivo pertence à organização.

        Serve de pista para um erro comum: o campus selecionado não corresponde ao
        da turma, de modo que os alunos estão em outra organização.
        """
        return self.total_alunos > 0 and self.total_alunos_encontrados == 0
