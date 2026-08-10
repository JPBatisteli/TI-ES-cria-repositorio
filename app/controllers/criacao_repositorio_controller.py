from typing import Callable, List, Optional, Tuple

from app.models.aluno import Aluno
from app.models.novo_repositorio import NovoRepositorio
from app.models.resultado_adicao_aluno import ResultadoAdicaoAluno, SituacaoAluno
from app.models.resultado_criacao import ResultadoCriacao
from app.models.verificacao_lote import VerificacaoGrupo, VerificacaoLote
from app.services.github_service import GithubService, GithubServiceError, RepositorioJaExisteError
from app.utils import github_utils


class CriacaoRepositorioController:
    """
    Coordena a criação de repositórios de Trabalho Interdisciplinar no GitHub.

    Responsável por validar a solicitação, verificar se o repositório já existe
    na organização do campus e, por fim, solicitar a criação ao GithubService.
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

    def criar_repositorio(self, novo_repositorio: NovoRepositorio) -> ResultadoCriacao:
        """
        Cria o repositório na organização correspondente ao campus selecionado.

        Args:
            novo_repositorio (NovoRepositorio): Dados informados pelo professor.

        Returns:
            ResultadoCriacao: Resultado da operação, com a URL do repositório
                              criado ou a lista de erros encontrados.
        """
        if not novo_repositorio.validar():
            return ResultadoCriacao.falha(novo_repositorio, novo_repositorio.erros)

        organizacao = novo_repositorio.campus.organizacao
        nome = novo_repositorio.nome

        try:
            if self.github_service.repositorio_existe(organizacao, nome):
                return ResultadoCriacao.falha(
                    novo_repositorio,
                    [self._mensagem_repositorio_duplicado(organizacao, nome)]
                )

            dados = self._gerar_repositorio(novo_repositorio, organizacao, nome)
        except RepositorioJaExisteError:
            # O repositório existe, mas não é visível para o token usado na verificação
            # prévia (repositório privado, por exemplo). A recusa vem da própria API.
            return ResultadoCriacao.falha(
                novo_repositorio,
                [self._mensagem_repositorio_duplicado(organizacao, nome)]
            )
        except GithubServiceError as erro:
            return ResultadoCriacao.falha(novo_repositorio, [str(erro)])

        resultado = ResultadoCriacao.criado(novo_repositorio, dados.get("html_url", novo_repositorio.url))

        if novo_repositorio.criar_equipe:
            resultado.equipe, resultado.erro_equipe = self._criar_equipe(novo_repositorio)

            if resultado.equipe:
                resultado.alunos = self.adicionar_alunos_na_equipe(novo_repositorio, resultado.equipe)
                # A remoção vem por último: se falhar, o repositório, a equipe e o
                # acesso dos alunos já estão prontos.
                resultado.aviso_equipe = self._remover_criador_da_equipe(organizacao, resultado.equipe)
                return resultado

        # Sem equipe — seja por opção do professor, seja porque a criação dela falhou —
        # os alunos recebem acesso individualmente, para não ficarem sem o repositório.
        resultado.alunos = self.adicionar_alunos(novo_repositorio)

        return resultado

    def _gerar_repositorio(self, novo_repositorio: NovoRepositorio, organizacao: str, nome: str) -> dict:
        """
        Cria o repositório, a partir do modelo do campus quando houver um.

        Todos os campi possuem modelo configurado, de modo que este é o caminho normal.
        A criação de repositório vazio permanece como alternativa para um campus que
        venha a ser cadastrado sem modelo.

        Args:
            novo_repositorio (NovoRepositorio): Solicitação validada.
            organizacao (str): Organização em que o repositório será criado.
            nome (str): Nome padronizado do repositório.

        Returns:
            dict: Dados do repositório criado, devolvidos pela API.

        Raises:
            GithubServiceError: Se a criação falhar.
        """
        if novo_repositorio.usa_template:
            template = novo_repositorio.template
            return self.github_service.criar_repositorio_por_template(
                template_owner=template.owner,
                template_repositorio=template.repositorio,
                nome_organizacao=organizacao,
                nome_repositorio=nome,
                descricao=novo_repositorio.descricao,
                privado=novo_repositorio.privado
            )

        return self.github_service.criar_repositorio(
            nome_organizacao=organizacao,
            nome_repositorio=nome,
            descricao=novo_repositorio.descricao,
            privado=novo_repositorio.privado
        )

    def _criar_equipe(self, novo_repositorio: NovoRepositorio) -> Tuple[str, str]:
        """
        Cria a equipe do repositório e concede-lhe a administração dele.

        Args:
            novo_repositorio (NovoRepositorio): Solicitação já criada no GitHub.

        Returns:
            Tuple[str, str]: Identificador da equipe e mensagem de erro. Apenas um
                             dos dois é preenchido.
        """
        organizacao = novo_repositorio.campus.organizacao

        try:
            slug = self.github_service.criar_equipe(
                nome_organizacao=organizacao,
                nome_equipe=novo_repositorio.nome_equipe,
                descricao=f"Equipe do Trabalho Interdisciplinar {novo_repositorio.disciplina.rotulo}."
            )

            self.github_service.definir_permissao_da_equipe(
                nome_organizacao=organizacao,
                slug_equipe=slug,
                nome_repositorio=novo_repositorio.nome,
                permissao=GithubService.PERMISSAO_ADMINISTRACAO
            )
        except GithubServiceError as erro:
            return "", str(erro)

        return slug, ""

    def _remover_criador_da_equipe(self, nome_organizacao: str, slug_equipe: str) -> str:
        """
        Remove da equipe o professor que a criou.

        O GitHub adiciona automaticamente como mantenedor quem cria uma equipe, sem
        oferecer forma de evitar isso. Como os professores são proprietários da
        organização, e proprietários administram todas as equipes independentemente de
        pertencerem a elas, a remoção não lhes custa acesso — apenas evita que se
        acumulem nas equipes de todas as turmas.

        A falha aqui não invalida nada do que já foi feito, por isso é devolvida como
        aviso e não como erro.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            slug_equipe (str): Identificador da equipe recém-criada.

        Returns:
            str: Aviso a ser exibido ao professor, ou string vazia se tudo correu bem.
        """
        try:
            professor = self.github_service.obter_usuario_autenticado()

            if not professor:
                return (
                    "A equipe foi criada, mas não foi possível identificar o usuário do "
                    "token para removê-lo dela."
                )

            self.github_service.remover_membro_da_equipe(nome_organizacao, slug_equipe, professor)
        except GithubServiceError as erro:
            return f"A equipe foi criada, mas você não pôde ser removido dela: {erro}"

        return ""

    def adicionar_alunos_na_equipe(
            self,
            novo_repositorio: NovoRepositorio,
            slug_equipe: str
    ) -> List[ResultadoAdicaoAluno]:
        """
        Adiciona os alunos à equipe que administra o repositório.

        Assim como na adição individual, cada aluno é tratado de forma independente e
        apenas os que já pertencem à organização são adicionados.

        Args:
            novo_repositorio (NovoRepositorio): Solicitação já criada no GitHub.
            slug_equipe (str): Identificador da equipe criada.

        Returns:
            List[ResultadoAdicaoAluno]: Desfecho da adição de cada aluno.
        """
        organizacao = novo_repositorio.campus.organizacao

        return [
            self._adicionar_aluno_na_equipe(organizacao, slug_equipe, aluno)
            for aluno in novo_repositorio.alunos_unicos
        ]

    def _adicionar_aluno_na_equipe(
            self,
            nome_organizacao: str,
            slug_equipe: str,
            aluno: Aluno
    ) -> ResultadoAdicaoAluno:
        """
        Adiciona um aluno à equipe, verificando antes se ele pertence à organização.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            slug_equipe (str): Identificador da equipe.
            aluno (Aluno): Aluno a ser adicionado.

        Returns:
            ResultadoAdicaoAluno: Situação resultante para esse aluno.
        """
        if not aluno.valido:
            return ResultadoAdicaoAluno(aluno=aluno, situacao=SituacaoAluno.USERNAME_INVALIDO)

        try:
            if not self.github_service.e_membro(nome_organizacao, aluno.username):
                return ResultadoAdicaoAluno(aluno=aluno, situacao=SituacaoAluno.FORA_DA_ORGANIZACAO)

            estado = self.github_service.adicionar_membro_na_equipe(
                nome_organizacao=nome_organizacao,
                slug_equipe=slug_equipe,
                username=aluno.username
            )
        except GithubServiceError as erro:
            return ResultadoAdicaoAluno(aluno=aluno, situacao=SituacaoAluno.ERRO, detalhe=str(erro))

        situacao = (
            SituacaoAluno.ADICIONADO_A_EQUIPE if estado == "active"
            else SituacaoAluno.CONVITE_ENVIADO
        )
        return ResultadoAdicaoAluno(aluno=aluno, situacao=situacao)

    def adicionar_alunos(self, novo_repositorio: NovoRepositorio) -> List[ResultadoAdicaoAluno]:
        """
        Adiciona os alunos informados como colaboradores do repositório.

        Cada aluno é tratado de forma independente: a falha de um não interrompe os
        demais, e o desfecho de cada um é registado individualmente.

        Args:
            novo_repositorio (NovoRepositorio): Solicitação já criada no GitHub.

        Returns:
            List[ResultadoAdicaoAluno]: Desfecho da adição de cada aluno.
        """
        organizacao = novo_repositorio.campus.organizacao
        nome = novo_repositorio.nome

        return [
            self._adicionar_aluno(organizacao, nome, aluno)
            for aluno in novo_repositorio.alunos_unicos
        ]

    def _adicionar_aluno(self, nome_organizacao: str, nome_repositorio: str, aluno: Aluno) -> ResultadoAdicaoAluno:
        """
        Adiciona um aluno ao repositório, verificando antes se ele pertence à organização.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            nome_repositorio (str): Nome do repositório recém-criado.
            aluno (Aluno): Aluno a ser adicionado.

        Returns:
            ResultadoAdicaoAluno: Situação resultante para esse aluno.
        """
        if not aluno.valido:
            return ResultadoAdicaoAluno(aluno=aluno, situacao=SituacaoAluno.USERNAME_INVALIDO)

        try:
            if not self.github_service.e_membro(nome_organizacao, aluno.username):
                return ResultadoAdicaoAluno(aluno=aluno, situacao=SituacaoAluno.FORA_DA_ORGANIZACAO)

            convite_criado = self.github_service.adicionar_colaborador(
                nome_organizacao=nome_organizacao,
                nome_repositorio=nome_repositorio,
                username=aluno.username,
                permissao=GithubService.PERMISSAO_ESCRITA
            )
        except GithubServiceError as erro:
            return ResultadoAdicaoAluno(aluno=aluno, situacao=SituacaoAluno.ERRO, detalhe=str(erro))

        situacao = SituacaoAluno.CONVITE_ENVIADO if convite_criado else SituacaoAluno.ACESSO_CONCEDIDO
        return ResultadoAdicaoAluno(aluno=aluno, situacao=situacao)

    def verificar_lote(self, solicitacoes: List[NovoRepositorio]) -> VerificacaoLote:
        """
        Verifica, sem criar nada, se as solicitações podem ser atendidas.

        As listas de membros e de equipes da organização são carregadas uma única vez
        e consultadas em memória, de modo que o custo cresce com o número de grupos,
        não com o número de alunos.

        Args:
            solicitacoes (List[NovoRepositorio]): Solicitações montadas a partir do arquivo.

        Returns:
            VerificacaoLote: Resultado da verificação de cada grupo.
        """
        verificacao = VerificacaoLote()

        if not solicitacoes:
            return verificacao

        organizacao = solicitacoes[0].campus.organizacao

        try:
            membros = {nome.lower() for nome in self.github_service.listar_membros(organizacao, papel="all")}
            equipes = {slug.lower() for slug in self.github_service.listar_equipes(organizacao)}
        except GithubServiceError as erro:
            verificacao.grupos = [
                VerificacaoGrupo(solicitacao=solicitacao, erro=str(erro))
                for solicitacao in solicitacoes
            ]
            return verificacao

        # O modelo é o mesmo para todos os grupos, por ser definido pelo campus.
        verificacao.erro_template = self._verificar_template(solicitacoes[0])

        # Guarda o resultado por nome de usuário, para não repetir a consulta quando o
        # mesmo aluno aparecer em mais de um grupo do arquivo.
        existencia_conhecida = {}

        verificacao.grupos = [
            self._verificar_grupo(organizacao, solicitacao, membros, equipes, existencia_conhecida)
            for solicitacao in solicitacoes
        ]

        return verificacao

    def _verificar_template(self, solicitacao: NovoRepositorio) -> str:
        """
        Verifica se o repositório-modelo do campus está utilizável.

        A consulta é feita uma única vez por lote, já que o modelo é definido pelo
        campus e vale para todos os grupos do arquivo.

        Args:
            solicitacao (NovoRepositorio): Qualquer solicitação do lote, usada apenas
                                           para obter o campus.

        Returns:
            str: Mensagem de erro, ou string vazia se o modelo estiver utilizável.
        """
        if not solicitacao.usa_template:
            return ""

        template = solicitacao.template

        try:
            if not self.github_service.e_template(template.owner, template.repositorio):
                return (
                    f"O repositório-modelo '{template}' não foi encontrado ou não está "
                    "marcado como template no GitHub. Confirme em Settings → Template "
                    "repository, na página do modelo."
                )
        except GithubServiceError as erro:
            return f"Não foi possível consultar o repositório-modelo '{template}': {erro}"

        return ""

    def _verificar_grupo(
            self,
            nome_organizacao: str,
            solicitacao: NovoRepositorio,
            membros: set,
            equipes: set,
            existencia_conhecida: dict
    ) -> VerificacaoGrupo:
        """
        Verifica um grupo: disponibilidade do repositório, da equipe e situação dos alunos.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            solicitacao (NovoRepositorio): Solicitação correspondente ao grupo.
            membros (set): Nomes de usuário dos membros da organização, em minúsculas.
            equipes (set): Slugs das equipes existentes, em minúsculas.
            existencia_conhecida (dict): Cache de contas já consultadas nesta verificação.

        Returns:
            VerificacaoGrupo: Resultado da verificação do grupo.
        """
        resultado = VerificacaoGrupo(solicitacao=solicitacao)

        try:
            resultado.repositorio_disponivel = not self.github_service.repositorio_existe(
                nome_organizacao, solicitacao.nome
            )
            resultado.equipe_disponivel = github_utils.gerar_slug(solicitacao.nome_equipe) not in equipes

            for aluno in solicitacao.alunos_unicos:
                self._classificar_aluno(aluno, membros, existencia_conhecida, resultado)
        except GithubServiceError as erro:
            resultado.erro = str(erro)

        return resultado

    def _classificar_aluno(self, aluno: Aluno, membros: set, existencia_conhecida: dict, resultado: VerificacaoGrupo):
        """
        Classifica um aluno entre encontrado, fora da organização, inexistente ou inválido.

        Args:
            aluno (Aluno): Aluno informado no arquivo.
            membros (set): Nomes de usuário dos membros da organização, em minúsculas.
            existencia_conhecida (dict): Cache de contas já consultadas nesta verificação.
            resultado (VerificacaoGrupo): Resultado do grupo, preenchido em conjunto.
        """
        if not aluno.valido:
            resultado.alunos_invalidos.append(aluno.username)
            return

        if aluno.username_normalizado in membros:
            resultado.alunos_encontrados.append(aluno.username)
            return

        if aluno.username_normalizado not in existencia_conhecida:
            existencia_conhecida[aluno.username_normalizado] = self.github_service.usuario_existe(aluno.username)

        if existencia_conhecida[aluno.username_normalizado]:
            resultado.alunos_fora_da_organizacao.append(aluno.username)
        else:
            resultado.alunos_inexistentes.append(aluno.username)

    def criar_repositorios_em_lote(
            self,
            solicitacoes: List[NovoRepositorio],
            ao_concluir_cada: Optional[Callable[[int, ResultadoCriacao], None]] = None
    ) -> List[ResultadoCriacao]:
        """
        Cria vários repositórios em sequência.

        Cada solicitação é independente: a falha de uma não interrompe as seguintes,
        e o desfecho de todas é devolvido.

        Args:
            solicitacoes (List[NovoRepositorio]): Solicitações a serem criadas.
            ao_concluir_cada (Optional[Callable]): Função chamada após cada criação,
                                                   recebendo o índice e o resultado.
                                                   Permite acompanhar o progresso.

        Returns:
            List[ResultadoCriacao]: Resultado de cada solicitação, na ordem original.
        """
        resultados = []

        for indice, solicitacao in enumerate(solicitacoes):
            resultado = self.criar_repositorio(solicitacao)
            resultados.append(resultado)

            if ao_concluir_cada:
                ao_concluir_cada(indice, resultado)

        return resultados

    def listar_membros_organizacao(self, nome_organizacao: str, papel: str = "member") -> List[str]:
        """
        Lista os nomes de usuário dos membros da organização.

        O papel padrão exclui os proprietários, que são os professores. O papel 'all'
        os inclui, o que é útil para testar o fluxo com contas próprias.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            papel (str): Papel a filtrar ('member' ou 'all').

        Returns:
            List[str]: Nomes de usuário disponíveis para seleção pelo professor.
        """
        return self.github_service.listar_membros(nome_organizacao, papel=papel)

    @staticmethod
    def _mensagem_repositorio_duplicado(nome_organizacao: str, nome_repositorio: str) -> str:
        """
        Monta a mensagem exibida quando o nome do repositório já está em uso.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            nome_repositorio (str): Nome do repositório que já existe.

        Returns:
            str: Mensagem orientando o professor sobre como prosseguir.
        """
        return (
            f"Já existe um repositório chamado '{nome_repositorio}' na organização "
            f"{nome_organizacao}. Altere o nome do repositório ou verifique se ele já "
            f"foi criado em {nome_organizacao}/{nome_repositorio}."
        )

    def validar_acesso_organizacao(self, nome_organizacao: str) -> Optional[str]:
        """
        Verifica se o token configurado consegue acessar a organização informada.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.

        Returns:
            Optional[str]: Mensagem de erro, ou None se o acesso estiver correto.
        """
        try:
            self.github_service.obter_organizacao(nome_organizacao)
        except GithubServiceError as erro:
            return str(erro)
        return None
