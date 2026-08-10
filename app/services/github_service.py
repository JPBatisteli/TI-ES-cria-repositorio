import time
from typing import Callable, List, Optional

import requests

from app import config

# Espera adotada quando o GitHub sinaliza excesso de requisições sem informar por
# quanto tempo aguardar.
SEGUNDOS_DE_ESPERA_PADRAO = 30

# Quantas vezes uma requisição barrada por limite é repetida antes de desistir.
MAXIMO_DE_TENTATIVAS = 3

# Métodos que criam ou alteram conteúdo, sujeitos ao limite de 80 requisições por
# minuto imposto pelo GitHub.
METODOS_DE_ESCRITA = frozenset({"post", "put", "patch", "delete"})

# Intervalo mínimo entre requisições de escrita. Equivale a 75 por minuto, mantendo
# margem sobre o teto de 80 e evitando o bloqueio antes que ele aconteça.
INTERVALO_MINIMO_ENTRE_ESCRITAS = 0.8


class GithubServiceError(Exception):
    """Erro de comunicação ou de permissão na interação com a API do GitHub."""


class LimiteDeRequisicoesError(GithubServiceError):
    """
    O GitHub recusou a requisição por excesso de chamadas em pouco tempo.

    É levantado apenas quando as repetições automáticas se esgotam. Distingue-se dos
    demais erros 403 porque a causa não é falta de permissão: basta aguardar.
    """


class RepositorioJaExisteError(GithubServiceError):
    """
    A organização já possui um repositório com o nome solicitado.

    É levantado quando a própria API do GitHub recusa a criação por duplicidade,
    situação que ocorre quando o repositório existente não é visível para o token
    usado na verificação prévia (por exemplo, um repositório privado).
    """


class GithubService:
    """
    Serviço para comunicação com a API do GitHub.

    Responsável por verificar a existência de repositórios e por criar novos
    repositórios dentro de uma organização.

    Attributes:
        URL_BASE (str): URL base da API do GitHub.
        token (str): Token de autenticação GitHub.
        headers (dict): Cabeçalhos HTTP usados nas requisições para a API.
    """

    URL_BASE = "https://api.github.com"
    PERMISSAO_ESCRITA = "push"
    PERMISSAO_ADMINISTRACAO = "admin"
    PRIVACIDADE_EQUIPE = "closed"
    ITENS_POR_PAGINA = 100

    def __init__(
            self,
            token: Optional[str] = None,
            ao_aguardar: Optional[Callable[[int, int], None]] = None,
            intervalo_entre_escritas: Optional[float] = None
    ):
        """
        Inicializa o serviço com o token de autenticação e configura os cabeçalhos HTTP.

        Args:
            token (Optional[str]): Token pessoal do GitHub. Se não for informado,
                                   é usado o token definido no arquivo .env.
            ao_aguardar (Optional[Callable]): Função chamada antes de cada espera por
                                              excesso de requisições, recebendo os
                                              segundos de espera e o número da tentativa.
                                              Permite informar o professor na interface.
            intervalo_entre_escritas (Optional[float]): Segundos de intervalo mínimo entre
                                                        requisições de escrita. Zero desliga
                                                        o controle de ritmo.
        """
        self.token = token or config.GITHUB_TOKEN
        self.ao_aguardar = ao_aguardar
        self.intervalo_entre_escritas = (
            INTERVALO_MINIMO_ENTRE_ESCRITAS if intervalo_entre_escritas is None
            else intervalo_entre_escritas
        )
        self._instante_da_ultima_escrita = 0.0
        self._usuario_autenticado: Optional[str] = None
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"token {self.token}"
        }

    def _controlar_ritmo(self, metodo: str):
        """
        Espaça as requisições de escrita para não ultrapassar o limite do GitHub.

        O GitHub permite 80 requisições de criação de conteúdo por minuto. Uma turma
        consome três escritas por grupo mais uma por aluno, o que ultrapassa esse teto
        numa turma de porte médio. Espaçar as chamadas evita o bloqueio em vez de
        reagir a ele.

        As consultas não são afetadas: só os métodos de escrita entram na conta.

        Args:
            metodo (str): Método HTTP em minúsculas.
        """
        if metodo not in METODOS_DE_ESCRITA or self.intervalo_entre_escritas <= 0:
            return

        decorrido = time.monotonic() - self._instante_da_ultima_escrita
        restante = self.intervalo_entre_escritas - decorrido

        if 0 < restante <= self.intervalo_entre_escritas:
            time.sleep(restante)

        self._instante_da_ultima_escrita = time.monotonic()

    def _executar(self, metodo: str, url: str, **parametros) -> requests.Response:
        """
        Executa uma requisição, repetindo-a quando barrada por excesso de chamadas.

        O GitHub responde 403 ou 429 quando os limites de requisição são ultrapassados.
        Nesse caso a requisição é repetida após a espera indicada pela própria API — ou
        após uma espera padrão, quando ela não informa o tempo.

        Args:
            metodo (str): Método HTTP em minúsculas ('get', 'post', 'put' ou 'delete').
            url (str): URL completa da requisição.
            **parametros: Demais argumentos repassados ao requests.

        Returns:
            requests.Response: Resposta da última tentativa realizada.
        """
        funcao = getattr(requests, metodo)

        for tentativa in range(1, MAXIMO_DE_TENTATIVAS + 1):
            self._controlar_ritmo(metodo)
            resposta = funcao(url, headers=self.headers, **parametros)

            if tentativa == MAXIMO_DE_TENTATIVAS or not self._e_limite_de_requisicoes(resposta):
                return resposta

            segundos = self._segundos_de_espera(resposta)

            if self.ao_aguardar:
                self.ao_aguardar(segundos, tentativa)

            time.sleep(segundos)

        return resposta

    @staticmethod
    def _e_limite_de_requisicoes(resposta: requests.Response) -> bool:
        """
        Identifica se a resposta indica excesso de requisições, e não falta de permissão.

        O GitHub usa 403 para os dois casos, por isso a distinção depende dos cabeçalhos
        e da mensagem devolvida.

        Args:
            resposta (requests.Response): Resposta devolvida pela API.

        Returns:
            bool: True se a recusa for por limite de requisições.
        """
        if resposta.status_code not in (403, 429):
            return False

        cabecalhos = getattr(resposta, "headers", {}) or {}

        if cabecalhos.get("Retry-After"):
            return True
        if cabecalhos.get("x-ratelimit-remaining") == "0":
            return True

        mensagem = ""
        try:
            mensagem = (resposta.json() or {}).get("message", "")
        except (ValueError, AttributeError):
            mensagem = getattr(resposta, "text", "") or ""

        mensagem = mensagem.lower()
        return "rate limit" in mensagem or "abuse detection" in mensagem

    @staticmethod
    def _segundos_de_espera(resposta: requests.Response) -> int:
        """
        Determina quanto aguardar antes de repetir uma requisição barrada.

        Respeita o cabeçalho 'Retry-After' quando presente e, na sua ausência, o
        'x-ratelimit-reset'. Sem nenhum dos dois, adota a espera padrão.

        Args:
            resposta (requests.Response): Resposta devolvida pela API.

        Returns:
            int: Segundos a aguardar.
        """
        cabecalhos = getattr(resposta, "headers", {}) or {}

        retry_after = str(cabecalhos.get("Retry-After", ""))
        if retry_after.isdigit():
            return max(1, int(retry_after))

        reset = str(cabecalhos.get("x-ratelimit-reset", ""))
        if reset.isdigit():
            faltam = int(reset) - int(time.time())
            if 0 < faltam <= 3600:
                return faltam

        return SEGUNDOS_DE_ESPERA_PADRAO

    def _tratar_erro(self, resposta: requests.Response, acao: str):
        """
        Converte respostas de erro da API do GitHub em mensagens compreensíveis.

        Args:
            resposta (requests.Response): Resposta devolvida pela API.
            acao (str): Descrição da ação que estava sendo executada.

        Raises:
            LimiteDeRequisicoesError: Se a recusa for por excesso de requisições.
            RepositorioJaExisteError: Se a criação for recusada por nome duplicado.
            GithubServiceError: Nos demais casos, com a mensagem adequada ao código de status.
        """
        if resposta.status_code == 401:
            raise GithubServiceError(
                "Token do GitHub inválido ou expirado. Verifique o token informado."
            )
        # Verificado antes da falta de permissão porque o GitHub usa 403 para os dois casos.
        if self._e_limite_de_requisicoes(resposta):
            raise LimiteDeRequisicoesError(
                f"O GitHub recusou a operação '{acao}' por excesso de requisições, e as "
                f"tentativas automáticas não foram suficientes. Não é problema de permissão: "
                f"aguarde alguns minutos e repita a operação."
            )
        if resposta.status_code == 403:
            raise GithubServiceError(
                f"Sem permissão para {acao}. Confirme se o token possui o escopo 'repo' "
                "e se você tem permissão de criação na organização."
            )
        if resposta.status_code == 404:
            raise GithubServiceError(
                f"Recurso não encontrado ao {acao}. Confirme o nome da organização e as "
                "permissões do token."
            )

        mensagem = resposta.text
        detalhes = []
        try:
            dados = resposta.json()
            mensagem = dados.get("message", mensagem)
            erros = dados.get("errors", [])
            detalhes = [erro.get("message", "") for erro in erros if erro.get("message")]
            if detalhes:
                mensagem = f"{mensagem} ({'; '.join(detalhes)})"
        except ValueError:
            pass

        if resposta.status_code == 422 and self._e_erro_de_nome_duplicado(detalhes):
            raise RepositorioJaExisteError(mensagem)

        raise GithubServiceError(f"Erro ao {acao}: {resposta.status_code} - {mensagem}")

    @staticmethod
    def _e_erro_de_nome_duplicado(detalhes: List[str]) -> bool:
        """
        Identifica, entre os erros devolvidos pela API, o que indica nome já utilizado.

        Args:
            detalhes (List[str]): Mensagens do campo 'errors' da resposta da API.

        Returns:
            bool: True se algum erro indicar que o nome já existe na conta.
        """
        return any("already exists" in detalhe.lower() for detalhe in detalhes)

    def obter_organizacao(self, nome_organizacao: str) -> dict:
        """
        Obtém os dados da organização no GitHub.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.

        Returns:
            dict: Dados da organização devolvidos pela API.

        Raises:
            GithubServiceError: Se a requisição falhar.
        """
        url = f"{self.URL_BASE}/orgs/{nome_organizacao}"
        resposta = self._executar("get", url)

        if resposta.status_code != 200:
            self._tratar_erro(resposta, f"buscar os dados da organização '{nome_organizacao}'")

        return resposta.json()

    def repositorio_existe(self, nome_organizacao: str, nome_repositorio: str) -> bool:
        """
        Verifica se um repositório já existe dentro da organização.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            nome_repositorio (str): Nome do repositório a ser verificado.

        Returns:
            bool: True se o repositório já existir, False caso contrário.

        Raises:
            GithubServiceError: Se a requisição falhar por um motivo diferente de 404.
        """
        url = f"{self.URL_BASE}/repos/{nome_organizacao}/{nome_repositorio}"
        resposta = self._executar("get", url)

        if resposta.status_code == 200:
            return True
        if resposta.status_code == 404:
            return False

        self._tratar_erro(resposta, f"verificar a existência do repositório '{nome_repositorio}'")

    def criar_repositorio(
            self,
            nome_organizacao: str,
            nome_repositorio: str,
            descricao: str = "",
            privado: bool = False,
            inicializar_readme: bool = True
    ) -> dict:
        """
        Cria um repositório dentro de uma organização no GitHub.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            nome_repositorio (str): Nome do repositório a ser criado.
            descricao (str): Descrição do repositório.
            privado (bool): Indica se o repositório deve ser privado.
            inicializar_readme (bool): Indica se o repositório deve ser criado com um README inicial.

        Returns:
            dict: Dados do repositório criado, devolvidos pela API.

        Raises:
            RepositorioJaExisteError: Se a organização já possuir um repositório com esse nome.
            GithubServiceError: Se a criação falhar por outro motivo.
        """
        url = f"{self.URL_BASE}/orgs/{nome_organizacao}/repos"
        dados = {
            "name": nome_repositorio,
            "description": descricao,
            "private": privado,
            "auto_init": inicializar_readme,
        }

        resposta = self._executar("post", url, json=dados)

        if resposta.status_code != 201:
            self._tratar_erro(resposta, f"criar o repositório '{nome_repositorio}'")

        return resposta.json()

    def criar_repositorio_por_template(
            self,
            template_owner: str,
            template_repositorio: str,
            nome_organizacao: str,
            nome_repositorio: str,
            descricao: str = "",
            privado: bool = False,
            incluir_todas_as_branches: bool = False
    ) -> dict:
        """
        Cria um repositório a partir de um repositório-modelo.

        O repositório gerado recebe a estrutura de arquivos do modelo num commit
        inicial único: o histórico, as issues e os pull requests do modelo não são
        copiados.

        Args:
            template_owner (str): Dono do repositório-modelo.
            template_repositorio (str): Nome do repositório-modelo.
            nome_organizacao (str): Organização em que o repositório será criado.
            nome_repositorio (str): Nome do repositório a ser criado.
            descricao (str): Descrição do repositório.
            privado (bool): Indica se o repositório deve ser privado.
            incluir_todas_as_branches (bool): Copia todas as branches do modelo, e não
                                              apenas a branch padrão.

        Returns:
            dict: Dados do repositório criado, devolvidos pela API.

        Raises:
            RepositorioJaExisteError: Se a organização já possuir um repositório com esse nome.
            GithubServiceError: Se a criação falhar por outro motivo.
        """
        url = f"{self.URL_BASE}/repos/{template_owner}/{template_repositorio}/generate"
        dados = {
            "owner": nome_organizacao,
            "name": nome_repositorio,
            "description": descricao,
            "private": privado,
            "include_all_branches": incluir_todas_as_branches,
        }

        resposta = self._executar("post", url, json=dados)

        if resposta.status_code != 201:
            self._tratar_erro(
                resposta,
                f"criar o repositório '{nome_repositorio}' a partir do modelo "
                f"'{template_owner}/{template_repositorio}'"
            )

        return resposta.json()

    def e_template(self, owner: str, nome_repositorio: str) -> bool:
        """
        Verifica se um repositório existe e está marcado como template no GitHub.

        Args:
            owner (str): Dono do repositório.
            nome_repositorio (str): Nome do repositório.

        Returns:
            bool: True se o repositório existir e for um template.

        Raises:
            GithubServiceError: Se a requisição falhar por motivo diferente de 404.
        """
        url = f"{self.URL_BASE}/repos/{owner}/{nome_repositorio}"
        resposta = self._executar("get", url)

        if resposta.status_code == 404:
            return False
        if resposta.status_code != 200:
            self._tratar_erro(resposta, f"consultar o repositório-modelo '{owner}/{nome_repositorio}'")

        return bool(resposta.json().get("is_template"))

    def listar_membros(self, nome_organizacao: str, papel: str = "member") -> List[str]:
        """
        Lista os nomes de usuário dos membros da organização.

        O papel padrão é 'member', que exclui os proprietários da organização. Como
        os professores são proprietários, o resultado corresponde aos alunos.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            papel (str): Papel a filtrar ('all', 'admin' ou 'member').

        Returns:
            List[str]: Nomes de usuário dos membros, em ordem alfabética.

        Raises:
            GithubServiceError: Se a requisição falhar.
        """
        url = f"{self.URL_BASE}/orgs/{nome_organizacao}/members"
        params = {"role": papel, "per_page": self.ITENS_POR_PAGINA, "page": 1}
        membros = []

        tem_mais_paginas = True

        while tem_mais_paginas:
            resposta = self._executar("get", url, params=params)

            if resposta.status_code != 200:
                self._tratar_erro(resposta, f"listar os membros da organização '{nome_organizacao}'")

            membros.extend(item["login"] for item in resposta.json())

            link_header = resposta.headers.get("Link", "")
            tem_mais_paginas = 'rel="next"' in link_header

            params["page"] += 1

        return sorted(membros, key=str.lower)

    def e_membro(self, nome_organizacao: str, username: str) -> bool:
        """
        Verifica se um usuário é membro da organização.

        A API responde 204 quando o usuário é membro e 404 quando não é. A resposta
        302 indica que o próprio autor da requisição não pertence à organização, o
        que impede a verificação.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            username (str): Nome de usuário a ser verificado.

        Returns:
            bool: True se o usuário for membro da organização.

        Raises:
            GithubServiceError: Se a requisição falhar ou não puder ser respondida.
        """
        url = f"{self.URL_BASE}/orgs/{nome_organizacao}/members/{username}"
        resposta = self._executar("get", url, allow_redirects=False)

        if resposta.status_code == 204:
            return True
        if resposta.status_code == 404:
            return False
        if resposta.status_code == 302:
            raise GithubServiceError(
                f"Não foi possível verificar a associação de '{username}': o token usado "
                f"não pertence à organização {nome_organizacao}."
            )

        self._tratar_erro(resposta, f"verificar se '{username}' é membro de {nome_organizacao}")

    def adicionar_colaborador(
            self,
            nome_organizacao: str,
            nome_repositorio: str,
            username: str,
            permissao: str = PERMISSAO_ESCRITA
    ) -> bool:
        """
        Adiciona um usuário como colaborador de um repositório.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            nome_repositorio (str): Nome do repositório.
            username (str): Nome de usuário do colaborador.
            permissao (str): Permissão concedida ('pull', 'triage', 'push', 'maintain' ou 'admin').

        Returns:
            bool: True se o GitHub criou um convite a ser aceito pelo usuário;
                  False se o acesso foi concedido imediatamente, o que ocorre
                  quando o usuário já é membro da organização.

        Raises:
            GithubServiceError: Se a operação falhar.
        """
        url = f"{self.URL_BASE}/repos/{nome_organizacao}/{nome_repositorio}/collaborators/{username}"
        resposta = self._executar("put", url, json={"permission": permissao})

        if resposta.status_code == 201:
            return True
        if resposta.status_code == 204:
            return False

        self._tratar_erro(resposta, f"adicionar '{username}' ao repositório '{nome_repositorio}'")

    def obter_usuario_autenticado(self) -> str:
        """
        Retorna o nome de usuário dono do token em uso.

        A aplicação precisa desse dado para remover o próprio professor das equipes
        que ela cria. O resultado é guardado na instância, de modo que um lote inteiro
        consome uma única consulta.

        Returns:
            str: Nome de usuário do dono do token.

        Raises:
            GithubServiceError: Se a requisição falhar.
        """
        if self._usuario_autenticado is None:
            resposta = self._executar("get", f"{self.URL_BASE}/user")

            if resposta.status_code != 200:
                self._tratar_erro(resposta, "identificar o usuário dono do token")

            self._usuario_autenticado = resposta.json().get("login", "")

        return self._usuario_autenticado

    def remover_membro_da_equipe(self, nome_organizacao: str, slug_equipe: str, username: str):
        """
        Remove um usuário de uma equipe da organização.

        Remover-se de uma equipe não custa acesso a quem é proprietário da organização:
        proprietários administram todas as equipes, sejam membros delas ou não.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            slug_equipe (str): Identificador da equipe.
            username (str): Nome de usuário a ser removido.

        Raises:
            GithubServiceError: Se a operação falhar.
        """
        url = f"{self.URL_BASE}/orgs/{nome_organizacao}/teams/{slug_equipe}/memberships/{username}"
        resposta = self._executar("delete", url)

        if resposta.status_code != 204:
            self._tratar_erro(resposta, f"remover '{username}' da equipe '{slug_equipe}'")

    def usuario_existe(self, username: str) -> bool:
        """
        Verifica se uma conta existe no GitHub.

        Usado para distinguir um nome de usuário digitado errado de um aluno que
        possui conta mas ainda não pertence à organização.

        Args:
            username (str): Nome de usuário a ser verificado.

        Returns:
            bool: True se a conta existir.

        Raises:
            GithubServiceError: Se a requisição falhar por outro motivo.
        """
        url = f"{self.URL_BASE}/users/{username}"
        resposta = self._executar("get", url)

        if resposta.status_code == 200:
            return True
        if resposta.status_code == 404:
            return False

        self._tratar_erro(resposta, f"verificar a existência do usuário '{username}'")

    def listar_equipes(self, nome_organizacao: str) -> List[str]:
        """
        Lista os identificadores (slugs) das equipes da organização.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.

        Returns:
            List[str]: Slugs das equipes existentes.

        Raises:
            GithubServiceError: Se a requisição falhar.
        """
        url = f"{self.URL_BASE}/orgs/{nome_organizacao}/teams"
        params = {"per_page": self.ITENS_POR_PAGINA, "page": 1}
        equipes = []

        tem_mais_paginas = True

        while tem_mais_paginas:
            resposta = self._executar("get", url, params=params)

            if resposta.status_code != 200:
                self._tratar_erro(resposta, f"listar as equipes da organização '{nome_organizacao}'")

            equipes.extend(item["slug"] for item in resposta.json())

            link_header = resposta.headers.get("Link", "")
            tem_mais_paginas = 'rel="next"' in link_header

            params["page"] += 1

        return equipes

    def criar_equipe(
            self,
            nome_organizacao: str,
            nome_equipe: str,
            descricao: str = "",
            privacidade: str = PRIVACIDADE_EQUIPE
    ) -> str:
        """
        Cria uma equipe dentro da organização.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            nome_equipe (str): Nome da equipe, que deve ser único na organização.
            descricao (str): Descrição da equipe.
            privacidade (str): 'closed' (visível aos membros) ou 'secret'.

        Returns:
            str: Identificador da equipe (slug), gerado pelo GitHub a partir do nome.

        Raises:
            GithubServiceError: Se a criação falhar, inclusive por nome já utilizado.
        """
        url = f"{self.URL_BASE}/orgs/{nome_organizacao}/teams"
        dados = {
            "name": nome_equipe,
            "description": descricao,
            "privacy": privacidade,
        }

        resposta = self._executar("post", url, json=dados)

        if resposta.status_code != 201:
            self._tratar_erro(resposta, f"criar a equipe '{nome_equipe}'")

        return resposta.json().get("slug", "")

    def definir_permissao_da_equipe(
            self,
            nome_organizacao: str,
            slug_equipe: str,
            nome_repositorio: str,
            permissao: str = PERMISSAO_ADMINISTRACAO
    ):
        """
        Concede a uma equipe acesso a um repositório da organização.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            slug_equipe (str): Identificador da equipe.
            nome_repositorio (str): Nome do repositório.
            permissao (str): Permissão concedida ('pull', 'triage', 'push', 'maintain' ou 'admin').

        Raises:
            GithubServiceError: Se a operação falhar.
        """
        url = (
            f"{self.URL_BASE}/orgs/{nome_organizacao}/teams/{slug_equipe}"
            f"/repos/{nome_organizacao}/{nome_repositorio}"
        )
        resposta = self._executar("put", url, json={"permission": permissao})

        if resposta.status_code != 204:
            self._tratar_erro(
                resposta,
                f"conceder acesso da equipe '{slug_equipe}' ao repositório '{nome_repositorio}'"
            )

    def adicionar_membro_na_equipe(
            self,
            nome_organizacao: str,
            slug_equipe: str,
            username: str,
            papel: str = "member"
    ) -> str:
        """
        Adiciona um usuário a uma equipe da organização.

        Args:
            nome_organizacao (str): Nome da organização no GitHub.
            slug_equipe (str): Identificador da equipe.
            username (str): Nome de usuário a ser adicionado.
            papel (str): Papel na equipe ('member' ou 'maintainer').

        Returns:
            str: Estado da associação ('active' para quem já é membro da organização,
                 'pending' para quem ainda precisa aceitar o convite).

        Raises:
            GithubServiceError: Se a operação falhar.
        """
        url = f"{self.URL_BASE}/orgs/{nome_organizacao}/teams/{slug_equipe}/memberships/{username}"
        resposta = self._executar("put", url, json={"role": papel})

        if resposta.status_code != 200:
            self._tratar_erro(resposta, f"adicionar '{username}' à equipe '{slug_equipe}'")

        return resposta.json().get("state", "")
