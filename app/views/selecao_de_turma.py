from typing import Optional, Tuple

import streamlit as st

from app.models.campus import Campus
from app.models.disciplina import Disciplina
from app.models.turma import Turno, listar_codigos, listar_disciplinas, listar_turnos


def selecionar_turma(campus: Campus, sufixo_de_chave: str = "") -> Tuple[Optional[Disciplina], str]:
    """
    Monta a seleção encadeada de disciplina, turno e código da turma.

    As opções vêm do catálogo de turmas do campus, de modo que o professor escolhe
    entre códigos existentes em vez de digitá-los. Isso elimina a classe de erro mais
    cara da aplicação: um código incorreto produz um repositório fora do padrão, o que
    só se manifesta no fim do semestre, na geração dos certificados.

    Os turnos exibidos dependem da disciplina — TI5 e TI6 são ofertados apenas à noite.

    Args:
        campus (Campus): Campus selecionado, que determina o catálogo.
        sufixo_de_chave (str): Sufixo das chaves dos widgets, para que a mesma seleção
                               possa ser usada em mais de uma aba.

    Returns:
        Tuple[Optional[Disciplina], str]: Disciplina e código escolhidos. Ambos vazios
                                          se o campus não tiver turmas cadastradas.
    """
    disciplinas = listar_disciplinas(campus.sigla)

    if not disciplinas:
        st.warning(
            f"Nenhuma turma cadastrada para o campus {campus.nome}. "
            "Atualize o catálogo em `app/models/turma.py`."
        )
        return None, ""

    coluna_disciplina, coluna_turno, coluna_codigo = st.columns([2, 3, 3])

    with coluna_disciplina:
        rotulo = st.selectbox(
            "Disciplina",
            [disciplina.rotulo for disciplina in disciplinas],
            key=f"disciplina{sufixo_de_chave}"
        )
        disciplina = Disciplina[rotulo]

    turnos = listar_turnos(campus.sigla, disciplina)

    with coluna_turno:
        rotulo_turno = st.selectbox(
            "Turno",
            [turno.rotulo for turno in turnos],
            key=f"turno{sufixo_de_chave}",
            help=(
                "TI5 e TI6 são ofertados apenas à noite."
                if len(turnos) == 1 else None
            )
        )
        turno = next(t for t in Turno if t.rotulo == rotulo_turno)

    codigos = listar_codigos(campus.sigla, disciplina, turno)

    with coluna_codigo:
        codigo = st.selectbox(
            "Código da turma",
            codigos,
            key=f"codigo{sufixo_de_chave}",
            help="Códigos ofertados neste campus, disciplina e turno."
        )

    return disciplina, codigo or ""
