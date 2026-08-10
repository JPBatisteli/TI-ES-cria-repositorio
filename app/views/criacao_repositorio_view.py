from datetime import datetime
from typing import List

import pandas as pd
import streamlit as st

from app.controllers.criacao_repositorio_controller import CriacaoRepositorioController
from app.models.aluno import Aluno
from app.models.campus import listar_nomes_campi, obter_campus
from app.models.disciplina import Disciplina
from app.models.novo_repositorio import NovoRepositorio
from app.models.periodo_letivo import PeriodoLetivo
from app.models.resultado_criacao import ResultadoCriacao
from app.services.github_service import GithubServiceError


@st.cache_data(ttl=3600, show_spinner="Carregando os membros da organização...")
def carregar_membros_organizacao(nome_organizacao: str, token: str, papel: str) -> List[str]:
    """
    Carrega os nomes de usuário dos membros da organização, mantendo-os em cache.

    A listagem é paginada e pode envolver várias requisições, por isso o resultado
    é reaproveitado por uma hora em vez de recarregado a cada interação da tela.

    Args:
        nome_organizacao (str): Nome da organização no GitHub.
        token (str): Token usado na consulta, que também compõe a chave do cache.
        papel (str): Papel a filtrar ('member' para apenas alunos, 'all' para incluir
                     os proprietários da organização).

    Returns:
        List[str]: Nomes de usuário dos membros da organização.
    """
    return CriacaoRepositorioController(token=token).listar_membros_organizacao(nome_organizacao, papel)


class CriacaoRepositorioView:
    """
    Interface gráfica para a criação dos repositórios dos Trabalhos Interdisciplinares.

    O professor seleciona o campus (que determina a organização no GitHub), a
    disciplina de TI, informa o código da disciplina e o nome do repositório.
    O nome padronizado é montado e exibido antes da criação.
    """

    def __init__(self):
        self.campus = None
        self.disciplina = None
        self.ano = PeriodoLetivo.atual().ano
        self.semestre = PeriodoLetivo.atual().semestre
        self.codigo_disciplina = ""
        self.nome_projeto = ""
        self.descricao = ""
        self.token = None
        self.alunos = []
        self.criar_equipe = False
        self.nome_equipe = ""

    def _criar_formulario(self):
        """Monta o formulário com os dados necessários para a criação do repositório."""
        st.subheader("Dados da disciplina")

        coluna_campus, coluna_disciplina, coluna_ano, coluna_semestre = st.columns([4, 2, 2, 2])

        with coluna_campus:
            nome_campus = st.selectbox("Campus", listar_nomes_campi())
            self.campus = obter_campus(nome_campus)

        with coluna_disciplina:
            rotulo_disciplina = st.selectbox("Disciplina", Disciplina.listar_rotulos())
            self.disciplina = Disciplina[rotulo_disciplina]

        periodo_atual = PeriodoLetivo.atual()

        with coluna_ano:
            self.ano = periodo_atual.ano
            st.selectbox("Ano", [periodo_atual.ano], disabled=True)

        with coluna_semestre:
            self.semestre = periodo_atual.semestre
            st.selectbox("Semestre", [periodo_atual.semestre], disabled=True)

        st.caption(f"Organização no GitHub: [{self.campus.organizacao}]({self.campus.url_organizacao})")
        st.caption(
            f"Período letivo **{periodo_atual}**, definido pela data de hoje "
            "(1º semestre de janeiro a 10 de julho; 2º semestre de 11 de julho a dezembro)."
        )

        st.subheader("Dados do repositório")

        coluna_codigo, coluna_nome = st.columns([2, 6])

        with coluna_codigo:
            self.codigo_disciplina = st.text_input(
                "Código da disciplina",
                placeholder="2401100",
                help="Código numérico da turma/disciplina no sistema acadêmico."
            )

        with coluna_nome:
            self.nome_projeto = st.text_input(
                "Nome do repositório",
                placeholder="Brechó Re-Use",
                help="Nome do projeto ou da equipe. Acentos e espaços são convertidos automaticamente."
            )

        self.descricao = st.text_input(
            "Descrição (opcional)",
            placeholder="Repositório do Trabalho Interdisciplinar da equipe."
        )

        self._criar_selecao_de_alunos()

    def _criar_selecao_de_alunos(self):
        """
        Monta o campo de seleção dos alunos que receberão acesso ao repositório.

        Os nomes de usuário dos membros da organização são carregados para permitir
        a busca por digitação. Caso a listagem falhe, o campo continua utilizável
        com a digitação manual dos nomes de usuário.
        """
        st.subheader("Alunos da equipe")

        self.criar_equipe = st.checkbox(
            "Criar uma equipe no GitHub para este repositório",
            value=False,
            help=(
                "A equipe passa a administrar o repositório. Os alunos entram na equipe "
                "em vez de serem adicionados individualmente."
            )
        )

        if self.criar_equipe:
            self._criar_campo_nome_da_equipe()

        incluir_professores = st.checkbox(
            "Incluir os proprietários da organização na lista",
            value=False,
            help=(
                "Os proprietários são os professores. Útil para testar o fluxo com "
                "contas próprias, já que por padrão a lista traz apenas os alunos."
            )
        )
        papel = "all" if incluir_professores else "member"

        membros = []
        aviso = ""

        if self.token:
            try:
                membros = carregar_membros_organizacao(self.campus.organizacao, self.token, papel)
            except GithubServiceError as erro:
                aviso = f"Não foi possível carregar os membros da organização: {erro}"
        else:
            aviso = "Informe o token do GitHub na barra lateral para carregar os membros da organização."

        usernames = st.multiselect(
            "Nomes de usuário no GitHub",
            options=membros,
            default=[],
            accept_new_options=True,
            filter_mode="contains",
            placeholder="Digite para buscar entre os membros da organização",
            help=(
                "Os alunos recebem permissão de escrita no repositório. É possível "
                "digitar um nome de usuário que não esteja na lista."
            )
        )

        self.alunos = [Aluno.de_texto(username) for username in usernames]

        if aviso:
            st.info(f"{aviso} A digitação manual continua disponível.")
        elif membros:
            st.caption(f"{len(membros)} membros carregados de {self.campus.organizacao}.")

    def _criar_campo_nome_da_equipe(self):
        """
        Monta o campo opcional com o nome da equipe.

        O campo nasce vazio e o nome derivado do repositório aparece como sugestão.
        Abaixo dele é exibido o nome que será efetivamente usado, deixando explícito
        se ele foi informado pelo professor ou gerado pela aplicação.
        """
        nome_derivado = self._montar_novo_repositorio().nome_equipe_derivado

        self.nome_equipe = st.text_input(
            "Nome da equipe (opcional)",
            value="",
            placeholder=nome_derivado or "Deixe em branco para usar o nome do repositório",
            help=(
                "Deixe em branco para que a equipe receba o mesmo nome do repositório. "
                "O nome precisa ser único na organização — nomes curtos e genéricos "
                "podem colidir com equipes de outras turmas ou semestres."
            )
        )

        if self.nome_equipe.strip():
            st.caption(f"Nome da equipe: **{self.nome_equipe.strip()}** (informado por você)")
        elif nome_derivado:
            st.caption(f"Nome da equipe: **{nome_derivado}** (derivado do nome do repositório)")
        else:
            st.caption(
                "O nome da equipe será derivado do nome do repositório assim que o "
                "código da disciplina e o nome do repositório forem preenchidos."
            )

    def _montar_novo_repositorio(self) -> NovoRepositorio:
        """
        Constrói o objeto NovoRepositorio a partir dos dados informados no formulário.

        Returns:
            NovoRepositorio: Solicitação de criação preenchida.
        """
        return NovoRepositorio(
            campus=self.campus,
            disciplina=self.disciplina,
            codigo_disciplina=self.codigo_disciplina,
            nome_projeto=self.nome_projeto,
            ano=int(self.ano),
            semestre=int(self.semestre),
            descricao=self.descricao,
            alunos=self.alunos,
            criar_equipe=self.criar_equipe,
            nome_equipe_personalizado=self.nome_equipe
        )

    @staticmethod
    def _exibir_previa(novo_repositorio: NovoRepositorio):
        """Exibe o nome padronizado que será usado na criação do repositório."""
        st.subheader("Prévia do repositório")
        st.code(novo_repositorio.nome, language="text")
        st.caption(f"Será criado em: {novo_repositorio.url}")
        st.caption(
            f"Privado, gerado a partir do modelo {novo_repositorio.template}"
            if novo_repositorio.usa_template
            else "Privado, sem repositório-modelo configurado para este campus"
        )

        alunos = novo_repositorio.alunos_unicos
        if alunos:
            nomes = ", ".join(aluno.username for aluno in alunos)
            permissao = "na equipe" if novo_repositorio.criar_equipe else "com permissão de escrita"
            st.caption(f"Alunos {permissao} ({len(alunos)}): {nomes}")

        if novo_repositorio.criar_equipe:
            origem = "informado" if novo_repositorio.equipe_com_nome_personalizado else "derivado automaticamente"
            st.caption(
                f"Equipe a ser criada: {novo_repositorio.nome_equipe} ({origem}) "
                "— administradora do repositório"
            )

    @staticmethod
    def _exibir_resultado_da_equipe(resultado: ResultadoCriacao):
        """
        Informa se a equipe foi criada e passou a administrar o repositório.

        Args:
            resultado (ResultadoCriacao): Resultado da criação já concluída.
        """
        if resultado.equipe:
            organizacao = resultado.novo_repositorio.campus.organizacao
            url_equipe = f"https://github.com/orgs/{organizacao}/teams/{resultado.equipe}"
            st.success(f"Equipe **{resultado.equipe}** criada como administradora do repositório.")
            st.markdown(f"🔗 [Abrir equipe no GitHub]({url_equipe})")

            if resultado.aviso_equipe:
                st.warning(resultado.aviso_equipe)
        elif resultado.erro_equipe:
            st.error(f"A equipe não pôde ser criada: {resultado.erro_equipe}")
            st.info("Os alunos receberam acesso individual ao repositório, com permissão de escrita.")

    @staticmethod
    def _exibir_resultado_dos_alunos(resultado: ResultadoCriacao):
        """
        Exibe, aluno a aluno, o desfecho da concessão de acesso ao repositório.

        Args:
            resultado (ResultadoCriacao): Resultado da criação já concluída.
        """
        if not resultado.alunos:
            return

        st.subheader("Acesso dos alunos")

        df = pd.DataFrame([
            {
                "Aluno": item.aluno.username,
                "Situação": item.descricao,
                "Adicionado?": "Sim" if item.sucesso else "Não",
            }
            for item in resultado.alunos
        ])

        st.dataframe(df, use_container_width=True, hide_index=True)

        problemas = resultado.alunos_com_problema
        if problemas:
            st.warning(
                f"{len(problemas)} de {len(resultado.alunos)} alunos não receberam acesso. "
                "O repositório foi criado normalmente e os alunos podem ser adicionados "
                "depois, pelo GitHub."
            )

    @staticmethod
    def _exibir_historico():
        """Exibe a tabela com os repositórios criados durante a sessão."""
        criados = st.session_state.get("repositorios_criados", [])

        if not criados:
            return

        st.divider()
        st.subheader("Repositórios criados nesta sessão")

        df = pd.DataFrame(criados).rename(columns={
            "campus": "Campus",
            "organizacao": "Organização",
            "disciplina": "Disciplina",
            "codigo_disciplina": "Código",
            "ano": "Ano",
            "semestre": "Semestre",
            "nome": "Repositório",
            "url": "Endereço do Repositório",
            "privado": "Privado?",
            "alunos": "Alunos com Acesso",
            "equipe": "Equipe"
        })

        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button(
            label="⬇️ Baixar lista como CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="repositorios-criados.csv",
            mime="text/csv"
        )

    def _criar_repositorio(self, novo_repositorio: NovoRepositorio):
        """
        Solicita a criação do repositório e exibe o resultado da operação.

        Args:
            novo_repositorio (NovoRepositorio): Solicitação preenchida pelo professor.
        """
        if not self.token:
            st.error("Informe o token do GitHub na barra lateral para criar o repositório.")
            return

        aviso = st.empty()

        def ao_aguardar(segundos: int, tentativa: int):
            aviso.warning(
                f"O GitHub limitou o número de requisições. Aguardando {segundos} segundos "
                f"antes de repetir (tentativa {tentativa})."
            )

        controller = CriacaoRepositorioController(token=self.token, ao_aguardar=ao_aguardar)

        with st.spinner(f"Criando o repositório '{novo_repositorio.nome}'..."):
            resultado = controller.criar_repositorio(novo_repositorio)

        aviso.empty()

        if resultado.sucesso:
            st.success(f"Repositório **{novo_repositorio.nome}** criado com sucesso.")
            st.markdown(f"🔗 [Abrir repositório no GitHub]({resultado.url})")

            criados = st.session_state.get("repositorios_criados", [])
            registro = novo_repositorio.to_dict()
            registro["url"] = resultado.url
            registro["alunos"] = resultado.total_alunos_adicionados
            registro["equipe"] = resultado.equipe
            criados.append(registro)
            st.session_state["repositorios_criados"] = criados

            self._exibir_resultado_da_equipe(resultado)
            self._exibir_resultado_dos_alunos(resultado)
        else:
            for erro in resultado.erros:
                st.error(erro)

    def render(self, token: str = ""):
        """
        Renderiza a aba de criação de um repositório por vez.

        Args:
            token (str): Token do GitHub informado na barra lateral.
        """
        self.token = token

        st.caption(
            "Cria um repositório de Trabalho Interdisciplinar na organização do campus, "
            "seguindo o padrão de nomenclatura adotado pela Engenharia de Software."
        )

        if "repositorios_criados" not in st.session_state:
            st.session_state["repositorios_criados"] = []

        self._criar_formulario()

        novo_repositorio = self._montar_novo_repositorio()

        dados_preenchidos = bool(self.codigo_disciplina.strip() and self.nome_projeto.strip())

        if dados_preenchidos:
            self._exibir_previa(novo_repositorio)

        criar = st.button(
            "Criar Repositório",
            type="primary",
            use_container_width=True,
            icon=":material/add_circle:",
            disabled=not dados_preenchidos
        )

        if criar:
            self._criar_repositorio(novo_repositorio)

        self._exibir_historico()
