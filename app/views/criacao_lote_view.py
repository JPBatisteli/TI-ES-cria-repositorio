import hashlib
from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st

from app.controllers.criacao_repositorio_controller import CriacaoRepositorioController
from app.models.arquivo_lote import ArquivoLote
from app.models.campus import listar_nomes_campi, obter_campus
from app.models.novo_repositorio import NovoRepositorio
from app.models.periodo_letivo import PeriodoLetivo
from app.models.resultado_criacao import ResultadoCriacao
from app.models.verificacao_lote import VerificacaoLote

ARQUIVO_DE_EXEMPLO = Path(__file__).resolve().parents[2] / "docs" / "exemplo-criacao-em-lote.txt"

# Usado apenas se o arquivo de exemplo não for encontrado, para que a interface
# continue mostrando o formato esperado.
MODELO_MINIMO = """TI: TI1
Codigo: 2401100

Repositorio: Adota Pet
Grupo: Grupo 1
Membros: ana-souza, bruno-lima, carla-dias

Repositorio: Brechó Re-Use
Grupo: Grupo 2
Membros: joao-silva, maria-dev
"""


def carregar_modelo_de_arquivo() -> str:
    """
    Carrega o arquivo de exemplo distribuído com o projeto.

    Manter um único arquivo evita que o modelo oferecido na interface e o exemplo
    documentado divirjam com o tempo.

    Returns:
        str: Conteúdo do arquivo de exemplo, ou um modelo mínimo se ele não existir.
    """
    try:
        return ARQUIVO_DE_EXEMPLO.read_text(encoding="utf-8")
    except OSError:
        return MODELO_MINIMO


class CriacaoLoteView:
    """
    Interface gráfica para a criação de vários repositórios a partir de um arquivo.

    O professor seleciona o campus e envia um arquivo `.txt` com a disciplina, o
    código da turma e um bloco por grupo. Cada grupo dá origem a um repositório com
    equipe própria, administradora do repositório.
    """

    def __init__(self):
        self.campus = None
        self.token = ""

    @staticmethod
    def _exibir_instrucoes():
        """Exibe o formato esperado do arquivo e disponibiliza um modelo para download."""
        with st.expander("Formato do arquivo", expanded=False):
            st.markdown(
                "O arquivo é lido linha a linha, no formato `Rótulo: valor`. "
                "Linhas vazias e linhas iniciadas por `#` são ignoradas, e cada grupo "
                "começa numa linha `Repositorio:`."
            )
            st.code(MODELO_MINIMO, language="text")
            st.markdown(
                "São aceitos, como sinônimos, `Disciplina:` para `TI:`, `Equipe:` para "
                "`Grupo:` e `Alunos:` para `Membros:`. Os membros podem ser separados "
                "por vírgula ou ponto e vírgula."
            )
            st.markdown(
                "O modelo abaixo vem comentado, com as instruções de preenchimento "
                "dentro do próprio arquivo."
            )
            st.download_button(
                label="⬇️ Baixar modelo comentado",
                data=carregar_modelo_de_arquivo(),
                file_name="modelo-criacao-em-lote.txt",
                mime="text/plain",
                key="baixar_modelo_lote"
            )

    def _criar_formulario(self):
        """Monta a seleção de campus e o envio do arquivo."""
        periodo_atual = PeriodoLetivo.atual()

        coluna_campus, coluna_periodo = st.columns([6, 4])

        with coluna_campus:
            nome_campus = st.selectbox("Campus", listar_nomes_campi(), key="campus_lote")
            self.campus = obter_campus(nome_campus)

        with coluna_periodo:
            st.selectbox("Período letivo", [str(periodo_atual)], disabled=True, key="periodo_lote")

        st.caption(f"Organização no GitHub: [{self.campus.organizacao}]({self.campus.url_organizacao})")

        if self.campus.template:
            st.caption(
                f"Repositório-modelo: [{self.campus.template}]({self.campus.template.url}) "
                "— os repositórios são privados e gerados a partir dele"
            )

    @staticmethod
    def _exibir_erros(arquivo: ArquivoLote):
        """Exibe os problemas que impedem o processamento do arquivo."""
        st.error(f"O arquivo possui {len(arquivo.erros)} problema(s) e não pode ser processado:")
        for erro in arquivo.erros:
            st.markdown(f"- {erro}")

    @staticmethod
    def _exibir_previa(arquivo: ArquivoLote, solicitacoes: List[NovoRepositorio]):
        """
        Exibe a tabela com os repositórios que serão criados.

        Args:
            arquivo (ArquivoLote): Arquivo já interpretado.
            solicitacoes (List[NovoRepositorio]): Solicitações montadas a partir dele.
        """
        st.subheader("Prévia")

        coluna1, coluna2, coluna3 = st.columns(3)
        with coluna1:
            st.metric("Disciplina", arquivo.disciplina.rotulo)
        with coluna2:
            st.metric("Grupos", len(arquivo.grupos))
        with coluna3:
            st.metric("Alunos", arquivo.total_alunos)

        df = pd.DataFrame([
            {
                "Repositório": solicitacao.nome,
                "Equipe": solicitacao.nome_equipe,
                "Alunos": len(solicitacao.alunos_unicos),
                "Avisos": "; ".join(grupo.avisos),
            }
            for grupo, solicitacao in zip(arquivo.grupos, solicitacoes)
        ])

        st.dataframe(df, use_container_width=True, hide_index=True)

        avisos = [linha for linha in df["Avisos"] if linha]
        if avisos:
            st.warning(
                f"{len(avisos)} grupo(s) com avisos. Eles não impedem a criação, mas "
                "vale conferir antes de prosseguir."
            )

    @staticmethod
    def _exibir_resultados(resultados: List[ResultadoCriacao]):
        """
        Exibe o desfecho de cada repositório e de cada aluno.

        Args:
            resultados (List[ResultadoCriacao]): Resultado de cada solicitação.
        """
        criados = [resultado for resultado in resultados if resultado.sucesso]

        st.subheader("Resultado")

        if len(resultados) < st.session_state.get("total_do_lote", len(resultados)):
            st.warning(
                f"A criação foi interrompida: {len(resultados)} de "
                f"{st.session_state['total_do_lote']} repositórios chegaram a ser processados. "
                "Os demais não foram criados — envie novamente o arquivo apenas com eles."
            )

        coluna1, coluna2, coluna3 = st.columns(3)
        with coluna1:
            st.metric("Repositórios criados", f"{len(criados)} de {len(resultados)}")
        with coluna2:
            st.metric("Equipes criadas", sum(1 for r in resultados if r.equipe))
        with coluna3:
            st.metric("Alunos com acesso", sum(r.total_alunos_adicionados for r in resultados))

        df = pd.DataFrame([
            {
                "Repositório": resultado.novo_repositorio.nome,
                "Criado?": "Sim" if resultado.sucesso else "Não",
                "Equipe": resultado.equipe or "—",
                "Alunos com acesso": f"{resultado.total_alunos_adicionados} de {len(resultado.alunos)}",
                "Problemas": "; ".join(resultado.erros + ([resultado.erro_equipe] if resultado.erro_equipe else [])),
                "URL": resultado.url,
            }
            for resultado in resultados
        ])

        st.dataframe(df, use_container_width=True, hide_index=True)

        st.download_button(
            label="⬇️ Baixar resultado como CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="criacao-em-lote.csv",
            mime="text/csv",
            key="baixar_resultado_lote"
        )

        avisos = [resultado.aviso_equipe for resultado in resultados if resultado.aviso_equipe]
        if avisos:
            st.warning(
                f"{len(avisos)} equipe(s) foram criadas, mas você não pôde ser removido "
                "delas. Isso não afeta o acesso dos alunos nem o seu."
            )

        CriacaoLoteView._exibir_alunos_com_problema(resultados)

    @staticmethod
    def _exibir_alunos_com_problema(resultados: List[ResultadoCriacao]):
        """Reúne, num único lugar, os alunos que não receberam acesso."""
        pendencias = [
            {
                "Repositório": resultado.novo_repositorio.nome,
                "Aluno": item.aluno.username,
                "Situação": item.descricao,
            }
            for resultado in resultados
            for item in resultado.alunos_com_problema
        ]

        if not pendencias:
            return

        st.subheader("Alunos sem acesso")
        st.caption(
            "Os repositórios foram criados normalmente. Estes alunos precisam ser "
            "adicionados depois, pela aba de criação individual ou pelo GitHub."
        )
        st.dataframe(pd.DataFrame(pendencias), use_container_width=True, hide_index=True)

    @staticmethod
    def _rotulo_do_botao(verificacao: VerificacaoLote) -> str:
        """
        Monta o rótulo do botão de criação conforme o que resta a fazer.

        Args:
            verificacao (VerificacaoLote): Resultado da verificação.

        Returns:
            str: Texto do botão.
        """
        quantidade = len(verificacao.grupos_a_criar)

        if quantidade == 0:
            return "Nada a criar"

        if verificacao.e_retomada:
            if quantidade == 1:
                return "Criar o repositório restante"
            return f"Criar os {quantidade} repositórios restantes"

        if quantidade == 1:
            return "Criar 1 repositório"
        return f"Criar {quantidade} repositórios"

    def _obter_verificacao(self, conteudo: str, solicitacoes: List[NovoRepositorio]) -> VerificacaoLote:
        """
        Verifica o arquivo, reaproveitando o resultado enquanto ele não mudar.

        A verificação consulta a API do GitHub, por isso não pode ser refeita a cada
        interação da tela. O resultado é guardado e só é recalculado quando o arquivo
        ou o campus mudam, ou quando o professor pede explicitamente.

        Args:
            conteudo (str): Conteúdo do arquivo enviado.
            solicitacoes (List[NovoRepositorio]): Solicitações montadas a partir dele.

        Returns:
            VerificacaoLote: Resultado da verificação.
        """
        chave = hashlib.sha256(f"{self.campus.organizacao}|{conteudo}".encode("utf-8")).hexdigest()

        if st.session_state.get("chave_verificacao_lote") != chave:
            controller = CriacaoRepositorioController(token=self.token)

            with st.spinner("Verificando os dados do arquivo no GitHub..."):
                verificacao = controller.verificar_lote(solicitacoes)

            st.session_state["chave_verificacao_lote"] = chave
            st.session_state["verificacao_lote"] = verificacao

        return st.session_state["verificacao_lote"]

    @staticmethod
    def _exibir_verificacao(verificacao: VerificacaoLote):
        """
        Exibe o resultado da verificação, grupo a grupo.

        Args:
            verificacao (VerificacaoLote): Resultado já calculado.
        """
        st.subheader("Verificação")

        aptos = len(verificacao.grupos) - len(verificacao.grupos_com_impedimento)

        coluna1, coluna2 = st.columns(2)
        with coluna1:
            st.metric("Grupos sem impedimento", f"{aptos} de {len(verificacao.grupos)}")
        with coluna2:
            st.metric(
                "Alunos encontrados",
                f"{verificacao.total_alunos_encontrados} de {verificacao.total_alunos}"
            )

        df = pd.DataFrame([
            {
                "Repositório": grupo.solicitacao.nome,
                "Nome disponível": "Sim" if grupo.repositorio_disponivel else "Não",
                "Equipe disponível": "Sim" if grupo.equipe_disponivel else "Não",
                "Alunos encontrados": f"{len(grupo.alunos_encontrados)} de {grupo.total_alunos}",
                "Impedimentos": " ".join(grupo.impedimentos),
            }
            for grupo in verificacao.grupos
        ])

        st.dataframe(df, use_container_width=True, hide_index=True)

        if verificacao.erro_template:
            st.error(verificacao.erro_template)

        if verificacao.grupos_com_problema:
            st.error(
                f"{len(verificacao.grupos_com_problema)} grupo(s) exigem correção. "
                "Ajuste o arquivo — ou a situação no GitHub — e envie novamente."
            )
        elif verificacao.e_retomada:
            ja_criados = len(verificacao.grupos_ja_criados)
            a_criar = len(verificacao.grupos_a_criar)

            existentes = (
                "1 grupo já existe e será ignorado" if ja_criados == 1
                else f"{ja_criados} grupos já existem e serão ignorados"
            )
            restantes = (
                "o repositório restante" if a_criar == 1
                else f"os {a_criar} repositórios restantes"
            )

            st.info(f"{existentes}. Serão criados apenas {restantes} — não é preciso editar o arquivo.")
        elif verificacao.pode_criar:
            st.success(
                "Todos os grupos foram verificados e não há impedimentos. "
                "A criação está liberada."
            )
        else:
            st.warning(
                "Todos os grupos do arquivo já existem na organização. Não há nada a criar."
            )

        if verificacao.grupos_possivelmente_incompletos:
            nomes = ", ".join(
                grupo.solicitacao.nome for grupo in verificacao.grupos_possivelmente_incompletos
            )
            st.warning(
                f"Estes repositórios já existem, mas estão sem equipe: {nomes}. "
                "Provavelmente a criação foi interrompida no meio deles. Como serão "
                "ignorados na retomada, confira pela aba de criação individual se os "
                "alunos receberam acesso."
            )

        if verificacao.nenhum_aluno_encontrado:
            st.info(
                "Nenhum aluno do arquivo pertence à organização selecionada. "
                "Verifique se o campus escolhido corresponde ao da turma."
            )

    def _criar_repositorios(self, solicitacoes: List[NovoRepositorio]):
        """
        Cria os repositórios do arquivo, exibindo o progresso.

        Args:
            solicitacoes (List[NovoRepositorio]): Solicitações a serem criadas.
        """
        barra = st.progress(0.0, text=f"Criando {len(solicitacoes)} repositórios — não feche a página.")
        aviso = st.empty()

        # A lista é preenchida a cada repositório concluído, e não ao final: se a
        # execução for interrompida, o professor ainda enxerga o que já foi criado.
        st.session_state["resultados_lote"] = []
        st.session_state["total_do_lote"] = len(solicitacoes)

        def ao_aguardar(segundos: int, tentativa: int):
            aviso.warning(
                f"O GitHub limitou o número de requisições. Aguardando {segundos} segundos "
                f"antes de repetir (tentativa {tentativa}). A criação continua em seguida — "
                "não feche nem recarregue a página."
            )

        def ao_concluir(indice: int, resultado: ResultadoCriacao):
            st.session_state["resultados_lote"].append(resultado)

            concluidos = indice + 1
            aviso.empty()
            barra.progress(
                concluidos / len(solicitacoes),
                text=f"{concluidos} de {len(solicitacoes)}: {resultado.novo_repositorio.nome}"
            )

        controller = CriacaoRepositorioController(token=self.token, ao_aguardar=ao_aguardar)

        controller.criar_repositorios_em_lote(solicitacoes, ao_concluir_cada=ao_concluir)
        barra.empty()
        aviso.empty()

        # A verificação anterior deixou de valer: os repositórios e as equipes que
        # constavam como disponíveis acabaram de ser criados.
        st.session_state.pop("chave_verificacao_lote", None)
        st.session_state.pop("verificacao_lote", None)

    def render(self, token: str = ""):
        """
        Renderiza a aba de criação em lote.

        Args:
            token (str): Token do GitHub informado na barra lateral.
        """
        self.token = token

        st.caption(
            "Cria vários repositórios de uma vez, a partir de um arquivo com os grupos "
            "da turma. Cada grupo recebe um repositório e uma equipe própria."
        )

        self._criar_formulario()
        self._exibir_instrucoes()

        arquivo_enviado = st.file_uploader(
            "Arquivo com os grupos",
            type=["txt"],
            key="arquivo_lote",
            help="Arquivo de texto no formato descrito acima."
        )

        if arquivo_enviado is None:
            return

        conteudo = arquivo_enviado.getvalue().decode("utf-8")
        arquivo = ArquivoLote.de_texto(conteudo)

        if not arquivo.valido:
            self._exibir_erros(arquivo)
            return

        solicitacoes = arquivo.montar_solicitacoes(self.campus)
        self._exibir_previa(arquivo, solicitacoes)

        if not self.token:
            st.info(
                "Informe o token do GitHub na barra lateral para que os dados do arquivo "
                "sejam verificados e a criação seja liberada."
            )
            return

        verificacao = self._obter_verificacao(conteudo, solicitacoes)
        self._exibir_verificacao(verificacao)

        # Numa retomada, apenas os grupos ainda não criados são enviados.
        pendentes = verificacao.solicitacoes_a_criar()
        rotulo = self._rotulo_do_botao(verificacao)

        coluna_criar, coluna_reverificar = st.columns([4, 1])

        with coluna_criar:
            criar = st.button(
                rotulo,
                type="primary",
                use_container_width=True,
                icon=":material/library_add:",
                disabled=not verificacao.pode_criar,
                help=None if verificacao.pode_criar else "Resolva os problemas para liberar a criação.",
                key="criar_lote"
            )

        with coluna_reverificar:
            reverificar = st.button(
                "Verificar de novo",
                use_container_width=True,
                icon=":material/refresh:",
                key="reverificar_lote"
            )

        if reverificar:
            st.session_state.pop("chave_verificacao_lote", None)
            st.rerun()

        if criar:
            self._criar_repositorios(pendentes)

        resultados = st.session_state.get("resultados_lote", [])
        if resultados:
            self._exibir_resultados(resultados)
