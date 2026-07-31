from dataclasses import dataclass
from datetime import date
from typing import Optional

# Data de corte entre os semestres letivos: o primeiro semestre vai de 1 de janeiro
# a 10 de julho e o segundo, de 11 de julho a 31 de dezembro.
ULTIMO_DIA_PRIMEIRO_SEMESTRE = (7, 10)


@dataclass(frozen=True)
class PeriodoLetivo:
    """
    Representa um período letivo, formado por ano e semestre.

    O período é determinado pela data corrente, e não escolhido livremente, para que
    os repositórios sejam sempre criados no semestre em andamento.

    Attributes:
        ano (int): Ano letivo.
        semestre (int): Semestre letivo (1 ou 2).
    """
    ano: int
    semestre: int

    @classmethod
    def atual(cls, data: Optional[date] = None) -> "PeriodoLetivo":
        """
        Determina o período letivo correspondente a uma data.

        O primeiro semestre compreende 1 de janeiro a 10 de julho; o segundo, 11 de
        julho a 31 de dezembro.

        Args:
            data (Optional[date]): Data de referência. Quando omitida, usa a data de hoje.

        Returns:
            PeriodoLetivo: Período letivo correspondente à data.
        """
        referencia = data or date.today()

        if (referencia.month, referencia.day) <= ULTIMO_DIA_PRIMEIRO_SEMESTRE:
            return cls(ano=referencia.year, semestre=1)

        return cls(ano=referencia.year, semestre=2)

    def __str__(self) -> str:
        return f"{self.ano}/{self.semestre}"
