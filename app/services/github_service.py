from typing import List, Optional

import requests

from app import config


class GithubServiceError(Exception):
    """Erro de comunicação ou de permissão na interação com a API do GitHub."""


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

    def __init__(self, token: Optional[str] = None):
        """
        Inicializa o serviço com o token de autenticação e configura os cabeçalhos HTTP.

        Args:
            token (Optional[str]): Token pessoal do GitHub. Se não for informado,
                                   é usado o token definido no arquivo .env.
        """
        self.token = token or config.GITHUB_TOKEN
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"token {self.token}"
        }

    def _tratar_erro(self, resposta: requests.Response, acao: str):
        """
        Converte respostas de erro da API do GitHub em mensagens compreensíveis.

        Args:
            resposta (requests.Response): Resposta devolvida pela API.
            acao (str): Descrição da ação que estava sendo executada.

        Raises:
            RepositorioJaExisteError: Se a criação for recusada por nome duplicado.
            GithubServiceError: Nos demais casos, com a mensagem adequada ao código de status.
        """
        if resposta.status_code == 401:
            raise GithubServiceError(
                "Token do GitHub inválido ou expirado. Verifique o token informado."
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
        resposta = requests.get(url, headers=self.headers)

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
        resposta = requests.get(url, headers=self.headers)

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

        resposta = requests.post(url, headers=self.headers, json=dados)

        if resposta.status_code != 201:
            self._tratar_erro(resposta, f"criar o repositório '{nome_repositorio}'")

        return resposta.json()

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
            resposta = requests.get(url, headers=self.headers, params=params)

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
        resposta = requests.get(url, headers=self.headers, allow_redirects=False)

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
        resposta = requests.put(url, headers=self.headers, json={"permission": permissao})

        if resposta.status_code == 201:
            return True
        if resposta.status_code == 204:
            return False

        self._tratar_erro(resposta, f"adicionar '{username}' ao repositório '{nome_repositorio}'")

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
        resposta = requests.get(url, headers=self.headers)

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
            resposta = requests.get(url, headers=self.headers, params=params)

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

        resposta = requests.post(url, headers=self.headers, json=dados)

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
        resposta = requests.put(url, headers=self.headers, json={"permission": permissao})

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
        resposta = requests.put(url, headers=self.headers, json={"role": papel})

        if resposta.status_code != 200:
            self._tratar_erro(resposta, f"adicionar '{username}' à equipe '{slug_equipe}'")

        return resposta.json().get("state", "")
