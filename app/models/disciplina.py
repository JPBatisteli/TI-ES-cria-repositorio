from enum import Enum
from typing import List


class Disciplina(Enum):
    """
    Enumeração das disciplinas de Trabalho Interdisciplinar (TI1 a TI6).

    O valor de cada membro é exatamente o trecho usado no nome padronizado
    do repositório (ex: 'ti1' em 'pmg-es-2025-1-ti1-2401100-projeto-x').
    """
    TI1 = "ti1"
    TI2 = "ti2"
    TI3 = "ti3"
    TI4 = "ti4"
    TI5 = "ti5"
    TI6 = "ti6"

    @property
    def rotulo(self) -> str:
        """Retorna o rótulo da disciplina para exibição na interface (ex: TI1)."""
        return self.name

    @classmethod
    def listar_rotulos(cls) -> List[str]:
        """
        Retorna os rótulos de todas as disciplinas, na ordem de TI1 a TI6.

        Returns:
            List[str]: Rótulos das disciplinas disponíveis para seleção.
        """
        return [disciplina.rotulo for disciplina in cls]

    def __str__(self) -> str:
        return self.rotulo
