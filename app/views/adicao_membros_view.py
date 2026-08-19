from typing import List

import pandas as pd
import streamlit as st

from app.controllers.adicao_membros_controller import AdicaoMembrosController
from app.models.aluno import Aluno
from app.models.campus import listar_nomes_campi, obter_campus
from app.models.lista_de_usuarios import ListaDeUsuarios
from app.models.resultado_adicao_membro import ResultadoAdicaoMembro
from app.views.criacao_repositorio_view import carregar_membros_organizacao

# Formato aceito no arquivo, exibido na interface e usado como modelo para download.
MODELO_DE_LISTA = """# Turma de TI1 - manhã
ana-souza
bruno-lima
carla-dias
"""

DESCRICAO_COMUM = (
    "Convida os alunos para a organização do campus. É a etapa anterior à criação dos "
    "repositórios: as abas de criação só concedem acesso a quem já pertence à "
    "organização, e apenas reportam quem está fora dela."
)


def selecionar_campus(sufixo_de_chave: str):
    """
    Monta a seleção do campus, que determina a organização de destino.

    Args:
        sufixo_de_chave (str): Sufixo das chaves dos widgets, para que a mesma seleção
                               possa ser usada em mais de uma aba.

    Returns:
        Campus: Campus escolhido pelo professor.
    """
    coluna_campus, _ = st.columns([6, 4])

    with coluna_campus:
        nome_campus = st.selectbox("Campus", listar_nomes_campi(), key=f"campus{sufixo_de_chave}")

    campus = obter_campus(nome_campus)
    st.caption(f"Organização no GitHub: [{campus.organizacao}]({campus.url_organizacao})")

    return campus


def exibir_resultados(resultados: List[ResultadoAdicaoMembro], sufixo_de_chave: str):
    """
    Exibe o desfecho de cada aluno e permite exportá-lo.

    Args:
        resultados (List[ResultadoAdicaoMembro]): Resultado de cada aluno.
        sufixo_de_chave (str): Sufixo das chaves dos widgets.
    """
    st.subheader("Resultado")

    convidados = [item for item in resultados if item.convite_pendente]
    ja_membros = [item for item in resultados if item.sucesso and not item.convite_pendente]
    com_problema = [item for item in resultados if not item.sucesso]

    coluna1, coluna2, coluna3 = st.columns(3)
    with coluna1:
        st.metric("Convites enviados", len(convidados))
    with coluna2:
        st.metric("Já eram membros", len(ja_membros))
    with coluna3:
        st.metric("Com problema", len(com_problema))

    df = pd.DataFrame([
        {
            "Aluno": item.aluno.username,
            "Situação": item.descricao,
            "Adicionado?": "Sim" if item.sucesso else "Não",
        }
        for item in resultados
    ])

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.download_button(
        label="⬇️ Baixar resultado como CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="alunos-na-organizacao.csv",
        mime="text/csv",
        key=f"baixar_resultado{sufixo_de_chave}"
    )

    if convidados:
        st.info(
            f"{len(convidados)} convite(s) ficam pendentes até que os alunos os aceitem — "
            "pelo e-mail do GitHub ou em github.com/orgs/. Crie os repositórios só depois "
            "disso, para que cada aluno receba acesso ao da sua equipe."
        )

    if com_problema:
        st.warning(
            f"{len(com_problema)} aluno(s) não foram adicionados. Confira a grafia dos "
            "nomes de usuário na tabela acima."
        )


def adicionar(campus, alunos: List[Aluno], token: str, chave_dos_resultados: str):
    """
    Convida os alunos para a organização, exibindo o progresso.

    Os resultados são gravados a cada aluno concluído: se a execução for interrompida,
    o professor ainda enxerga quem já foi convidado.

    Args:
        campus (Campus): Campus selecionado, que determina a organização.
        alunos (List[Aluno]): Alunos a convidar.
        token (str): Token do GitHub.
        chave_dos_resultados (str): Chave sob a qual guardar os resultados na sessão.
    """
    aviso = st.empty()

    def ao_aguardar(segundos: int, tentativa: int):
        aviso.warning(
            f"O GitHub limitou o número de requisições. Aguardando {segundos} segundos "
            f"antes de repetir (tentativa {tentativa}). A operação continua em seguida — "
            "não feche nem recarregue a página."
        )

    controller = AdicaoMembrosController(token=token, ao_aguardar=ao_aguardar)
    barra = st.progress(0.0, text=f"Convidando {len(alunos)} aluno(s) — não feche a página.")

    st.session_state[chave_dos_resultados] = []

    def ao_concluir(indice: int, resultado: ResultadoAdicaoMembro):
        st.session_state[chave_dos_resultados].append(resultado)

        concluidos = indice + 1
        aviso.empty()
        barra.progress(
            concluidos / len(alunos),
            text=f"{concluidos} de {len(alunos)}: {resultado.aluno.username}"
        )

    controller.adicionar_membros(campus.organizacao, alunos, ao_concluir_cada=ao_concluir)

    barra.empty()
    aviso.empty()

    # A composição da organização mudou: a listagem guardada pelas abas de criação
    # deixaria de fora quem acabou de entrar, e continuaria assim por uma hora.
    carregar_membros_organizacao.clear()


class AdicaoMembroView:
    """
    Interface gráfica para adicionar um aluno por vez à organização do campus.

    Serve ao caso pontual — o aluno que chegou depois, ou aquele cujo convite falhou
    no envio da turma inteira.
    """

    def render(self, token: str = ""):
        """
        Renderiza a aba de adição individual.

        Args:
            token (str): Token do GitHub informado na barra lateral.
        """
        st.caption(f"{DESCRICAO_COMUM} Esta aba trata de um aluno por vez.")

        campus = selecionar_campus("_membro")

        coluna_username, _ = st.columns([6, 4])

        with coluna_username:
            texto = st.text_input(
                "Nome de usuário no GitHub",
                placeholder="ana-souza",
                key="username_membro",
                help="Nome de usuário do aluno no GitHub. O '@' inicial é opcional."
            )

        aluno = Aluno.de_texto(texto)

        if not aluno.username:
            return

        if not aluno.valido:
            st.error(
                f"'{aluno.username}' não é um nome de usuário válido no GitHub. São "
                "aceitos letras, dígitos e hífens, até 39 caracteres."
            )
            return

        if not token:
            st.info("Informe o token do GitHub na barra lateral para adicionar o aluno.")
            return

        adicionar_aluno = st.button(
            f"Adicionar {aluno.username} à organização",
            type="primary",
            use_container_width=True,
            icon=":material/person_add:",
            key="adicionar_membro"
        )

        if adicionar_aluno:
            adicionar(campus, [aluno], token, "resultados_membro")

        resultados = st.session_state.get("resultados_membro", [])
        if resultados:
            exibir_resultados(resultados, "_membro")


class AdicaoMembrosLoteView:
    """
    Interface gráfica para adicionar vários alunos à organização a partir de um arquivo.

    O arquivo traz um nome de usuário por linha, formato deliberadamente mínimo para
    que a lista possa ser montada a partir de qualquer origem.
    """

    def render(self, token: str = ""):
        """
        Renderiza a aba de adição em lote.

        Args:
            token (str): Token do GitHub informado na barra lateral.
        """
        st.caption(f"{DESCRICAO_COMUM} Esta aba recebe a lista da turma num arquivo.")

        campus = selecionar_campus("_membros_lote")

        self._exibir_instrucoes()

        arquivo_enviado = st.file_uploader(
            "Lista de alunos",
            type=["txt"],
            key="arquivo_membros",
            help="Arquivo de texto com um nome de usuário do GitHub por linha."
        )

        if arquivo_enviado is None:
            return

        lista = ListaDeUsuarios.de_texto(arquivo_enviado.getvalue().decode("utf-8"))

        for aviso in lista.avisos:
            st.info(aviso)

        if not lista.valido:
            st.error(f"O arquivo possui {len(lista.erros)} problema(s) e não pode ser processado:")
            for erro in lista.erros:
                st.markdown(f"- {erro}")
            return

        self._exibir_previa(lista, campus)

        if not token:
            st.info("Informe o token do GitHub na barra lateral para adicionar os alunos.")
            return

        quantidade = len(lista.alunos)
        rotulo = (
            "Adicionar 1 aluno à organização" if quantidade == 1
            else f"Adicionar {quantidade} alunos à organização"
        )

        adicionar_alunos = st.button(
            rotulo,
            type="primary",
            use_container_width=True,
            icon=":material/group_add:",
            key="adicionar_membros_lote"
        )

        if adicionar_alunos:
            adicionar(campus, lista.alunos, token, "resultados_membros_lote")

        resultados = st.session_state.get("resultados_membros_lote", [])
        if resultados:
            exibir_resultados(resultados, "_membros_lote")

    @staticmethod
    def _exibir_instrucoes():
        """Exibe o formato esperado do arquivo e disponibiliza um modelo para download."""
        with st.expander("Formato do arquivo", expanded=False):
            st.markdown(
                "Um nome de usuário do GitHub **por linha**. Linhas vazias e linhas "
                "iniciadas por `#` são ignoradas."
            )
            st.code(MODELO_DE_LISTA, language="text")
            st.markdown(
                "O `@` inicial é aceito, e vários nomes podem ficar na mesma linha "
                "separados por vírgula ou ponto e vírgula. Nomes repetidos são "
                "considerados uma única vez."
            )
            st.download_button(
                label="⬇️ Baixar modelo",
                data=MODELO_DE_LISTA,
                file_name="modelo-lista-de-alunos.txt",
                mime="text/plain",
                key="baixar_modelo_membros"
            )

    @staticmethod
    def _exibir_previa(lista: ListaDeUsuarios, campus):
        """
        Exibe quem será convidado, antes de qualquer chamada à API.

        Args:
            lista (ListaDeUsuarios): Lista já interpretada.
            campus (Campus): Campus selecionado.
        """
        st.subheader("Prévia")

        coluna1, coluna2 = st.columns(2)
        with coluna1:
            st.metric("Organização", campus.organizacao)
        with coluna2:
            st.metric("Alunos na lista", len(lista.alunos))

        if lista.invalidos:
            st.warning(
                f"{len(lista.invalidos)} nome(s) de usuário fora das regras do GitHub, "
                f"que serão apenas reportados: {', '.join(lista.invalidos)}."
            )

        st.dataframe(
            pd.DataFrame([{"Aluno": aluno.username} for aluno in lista.alunos]),
            use_container_width=True,
            hide_index=True
        )
