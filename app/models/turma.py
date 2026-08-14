from enum import Enum
from typing import Dict, List, Tuple

from app.models.disciplina import Disciplina


class Turno(Enum):
    """
    Turno em que a turma é ofertada.

    O valor de cada membro é o rótulo exibido na interface.
    """
    MANHA = "Manhã"
    NOITE = "Noite"

    @property
    def rotulo(self) -> str:
        """Retorna o rótulo do turno para exibição na interface."""
        return self.value

    def __str__(self) -> str:
        return self.rotulo


# Códigos das turmas ofertadas, por campus, disciplina e turno.
#
# ATUALIZAR A CADA SEMESTRE: os códigos mudam de um período para outro. Esta é a
# única fonte de verdade da aplicação — a interface monta as opções a partir daqui,
# de modo que o professor nunca digita um código à mão.
#
# TI5 e TI6 são ofertados apenas à noite, o que se expressa pela ausência do turno
# da manhã, sem necessidade de regra no código.
CODIGOS_POR_TURMA: Dict[str, Dict[Disciplina, Dict[Turno, Tuple[str, ...]]]] = {
    # Coração Eucarístico
    "pmg": {
        Disciplina.TI1: {Turno.MANHA: ("0427100", "0427200"), Turno.NOITE: ("0438100", "0438200")},
        Disciplina.TI2: {Turno.MANHA: ("8183100", "8183200"), Turno.NOITE: ("8243100", "8243200")},
        Disciplina.TI3: {Turno.MANHA: ("9545100",),           Turno.NOITE: ("9577100",)},
        Disciplina.TI4: {Turno.MANHA: ("3126100",),           Turno.NOITE: ("3170100",)},
        Disciplina.TI5: {                                     Turno.NOITE: ("6904100",)},
        Disciplina.TI6: {                                     Turno.NOITE: ("9623100",)},
    },
    # Lourdes
    "plf": {
        Disciplina.TI1: {Turno.MANHA: ("7620100",), Turno.NOITE: ("7641100",)},
        Disciplina.TI2: {Turno.MANHA: ("7587100",), Turno.NOITE: ("7600100",)},
        Disciplina.TI3: {Turno.MANHA: ("8966100",), Turno.NOITE: ("5533100",)},
        Disciplina.TI4: {Turno.MANHA: ("1247100",), Turno.NOITE: ("1254100",)},
        Disciplina.TI5: {                           Turno.NOITE: ("0492100",)},
        Disciplina.TI6: {                           Turno.NOITE: ("8508100",)},
    },
}


def listar_disciplinas(sigla_campus: str) -> List[Disciplina]:
    """
    Lista as disciplinas ofertadas no campus, na ordem de TI1 a TI6.

    Args:
        sigla_campus (str): Sigla do campus (ex: 'pmg').

    Returns:
        List[Disciplina]: Disciplinas com turmas cadastradas.
    """
    ofertadas = CODIGOS_POR_TURMA.get(sigla_campus, {})
    return [disciplina for disciplina in Disciplina if disciplina in ofertadas]


def listar_turnos(sigla_campus: str, disciplina: Disciplina) -> List[Turno]:
    """
    Lista os turnos em que a disciplina é ofertada no campus.

    Args:
        sigla_campus (str): Sigla do campus.
        disciplina (Disciplina): Disciplina selecionada.

    Returns:
        List[Turno]: Turnos disponíveis, manhã antes de noite.
    """
    turnos = CODIGOS_POR_TURMA.get(sigla_campus, {}).get(disciplina, {})
    return [turno for turno in Turno if turno in turnos]


def listar_codigos(sigla_campus: str, disciplina: Disciplina, turno: Turno) -> List[str]:
    """
    Lista os códigos das turmas de uma disciplina num turno.

    Args:
        sigla_campus (str): Sigla do campus.
        disciplina (Disciplina): Disciplina selecionada.
        turno (Turno): Turno selecionado.

    Returns:
        List[str]: Códigos das turmas ofertadas.
    """
    return list(CODIGOS_POR_TURMA.get(sigla_campus, {}).get(disciplina, {}).get(turno, ()))


def codigo_valido(sigla_campus: str, codigo: str) -> bool:
    """
    Verifica se um código pertence a alguma turma cadastrada do campus.

    Args:
        sigla_campus (str): Sigla do campus.
        codigo (str): Código a ser verificado.

    Returns:
        bool: True se o código constar no catálogo do campus.
    """
    disciplinas = CODIGOS_POR_TURMA.get(sigla_campus, {})
    return any(
        codigo in codigos
        for turnos in disciplinas.values()
        for codigos in turnos.values()
    )
