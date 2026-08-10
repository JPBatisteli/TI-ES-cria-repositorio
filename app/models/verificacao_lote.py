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
    def ja_existe(self) -> bool:
        """
        Indica que o repositório do grupo já está criado na organização.

        Numa retomada, esses grupos são ignorados em vez de bloquearem os demais.
        """
        return not self.repositorio_disponivel

    @property
    def possivelmente_incompleto(self) -> bool:
        """
        Indica um grupo cujo repositório existe mas cuja equipe não foi criada.

        É o sintoma de um lote interrompido no meio do grupo: o repositório chegou a
        ser criado, mas a equipe e o acesso dos alunos não. Como a retomada ignora
        repositórios já existentes, esse caso precisa ser conferido à parte.
        """
        return self.ja_existe and self.equipe_disponivel and self.solicitacao.criar_equipe

    @property
    def problemas(self) -> List[str]:
        """
        Retorna os problemas que exigem correção antes de criar o grupo.

        Não inclui o repositório já existente, que é tratado como grupo concluído e
        não como erro a corrigir.

        Returns:
            List[str]: Mensagens descrevendo cada problema encontrado.
        """
        problemas = []

        if self.erro:
            problemas.append(self.erro)
        # Equipe ocupada sem repositório correspondente indica colisão de nome, e não
        # um grupo já criado por este mesmo arquivo.
        if not self.equipe_disponivel and not self.ja_existe:
            problemas.append(f"A equipe '{self.solicitacao.nome_equipe}' já existe na organização.")
        if self.alunos_invalidos:
            problemas.append(
                f"Nome de usuário inválido: {', '.join(self.alunos_invalidos)}."
            )
        if self.alunos_inexistentes:
            problemas.append(
                f"Não existe no GitHub: {', '.join(self.alunos_inexistentes)}."
            )
        if self.alunos_fora_da_organizacao:
            problemas.append(
                f"Fora da organização: {', '.join(self.alunos_fora_da_organizacao)}."
            )

        return problemas

    @property
    def impedimentos(self) -> List[str]:
        """
        Retorna tudo que impede a criação deste grupo, inclusive já estar criado.

        Returns:
            List[str]: Mensagens descrevendo cada impedimento encontrado.
        """
        impedimentos = []

        if self.ja_existe:
            impedimentos.append(f"O repositório '{self.solicitacao.nome}' já existe na organização.")

        return impedimentos + self.problemas

    @property
    def apto(self) -> bool:
        """Indica que o grupo pode ser criado agora, sem problemas conhecidos."""
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
        erro_template (str): Problema com o repositório-modelo do campus. Impede a
                             criação de todos os grupos, já que o modelo é comum a eles.
    """
    grupos: List[VerificacaoGrupo] = field(default_factory=list)
    erro_template: str = ""

    @property
    def apto(self) -> bool:
        """Indica que todos os grupos podem ser criados, nenhum deles já existindo."""
        return bool(self.grupos) and all(grupo.apto for grupo in self.grupos)

    @property
    def grupos_com_impedimento(self) -> List[VerificacaoGrupo]:
        """Retorna os grupos que possuem ao menos um impedimento."""
        return [grupo for grupo in self.grupos if not grupo.apto]

    @property
    def grupos_a_criar(self) -> List[VerificacaoGrupo]:
        """Retorna os grupos que ainda serão criados."""
        return [grupo for grupo in self.grupos if grupo.apto]

    @property
    def grupos_ja_criados(self) -> List[VerificacaoGrupo]:
        """Retorna os grupos cujo repositório já existe na organização."""
        return [grupo for grupo in self.grupos if grupo.ja_existe]

    @property
    def grupos_com_problema(self) -> List[VerificacaoGrupo]:
        """
        Retorna os grupos que exigem correção antes de prosseguir.

        Diferencia-se de 'grupos_com_impedimento' por não incluir os grupos que apenas
        já foram criados: estes não precisam de correção, apenas são ignorados.
        """
        return [grupo for grupo in self.grupos if grupo.problemas]

    @property
    def grupos_possivelmente_incompletos(self) -> List[VerificacaoGrupo]:
        """Retorna os grupos criados sem equipe, sintoma de interrupção no meio."""
        return [grupo for grupo in self.grupos if grupo.possivelmente_incompleto]

    @property
    def e_retomada(self) -> bool:
        """Indica que parte dos grupos já existe e o restante ainda pode ser criado."""
        return bool(self.grupos_ja_criados) and bool(self.grupos_a_criar)

    @property
    def pode_criar(self) -> bool:
        """
        Indica que a criação pode prosseguir.

        Exige que haja algo a criar, que nenhum grupo apresente problema a corrigir e
        que o repositório-modelo do campus esteja utilizável. Grupos já existentes não
        bloqueiam: permitem retomar um lote interrompido sem que o professor precise
        editar o arquivo.
        """
        return bool(self.grupos_a_criar) and not self.grupos_com_problema and not self.erro_template

    def solicitacoes_a_criar(self) -> List:
        """
        Retorna as solicitações dos grupos que ainda serão criados.

        Returns:
            List[NovoRepositorio]: Solicitações pendentes, na ordem do arquivo.
        """
        return [grupo.solicitacao for grupo in self.grupos_a_criar]

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
