from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.models.disciplina import Disciplina
from app.models.template import Template


@dataclass(frozen=True)
class Campus:
    """
    Representa um campus da PUC Minas onde as disciplinas de Trabalho
    Interdisciplinar (TI) são lecionadas.

    O campus determina duas coisas no momento da criação de um repositório:
    a organização do GitHub em que ele será criado e a sigla usada como
    prefixo do nome padronizado.

    Attributes:
        sigla (str): Sigla usada como prefixo do nome do repositório (ex: pmg, plf).
        nome (str): Nome do campus (ex: Coração Eucarístico).
        organizacao (str): Nome da organização no GitHub (ex: ICEI-PUC-Minas-PMGES-TI).
        template (Optional[Template]): Repositório-modelo adotado por padrão no campus.
                                       Quando ausente, os repositórios são criados vazios.
        templates_por_disciplina (Dict[Disciplina, Template]): Modelos específicos de
                                       determinadas disciplinas, que prevalecem sobre o
                                       padrão. Usado quando um TI adota um modelo próprio.
        curso (str): Nome do curso associado. Valor padrão: "Engenharia de Software".
    """
    sigla: str
    nome: str
    organizacao: str
    template: Optional[Template] = None
    templates_por_disciplina: Dict[Disciplina, Template] = field(default_factory=dict)
    curso: str = "Engenharia de Software"

    def template_para(self, disciplina: Optional[Disciplina]) -> Optional[Template]:
        """
        Retorna o repositório-modelo a ser usado pela disciplina.

        Disciplinas com modelo próprio prevalecem sobre o modelo padrão do campus.

        Args:
            disciplina (Optional[Disciplina]): Disciplina do repositório.

        Returns:
            Optional[Template]: Modelo aplicável, ou None se o campus não tiver nenhum.
        """
        if disciplina is not None and disciplina in self.templates_por_disciplina:
            return self.templates_por_disciplina[disciplina]

        return self.template

    @property
    def url_organizacao(self) -> str:
        """Retorna a URL da organização do campus no GitHub."""
        return f"https://github.com/{self.organizacao}"

    def __str__(self) -> str:
        return f"{self.nome} ({self.sigla.upper()})"


CAMPI: Dict[str, Campus] = {
    "Coração Eucarístico": Campus(
        sigla="pmg",
        nome="Coração Eucarístico",
        organizacao="ICEI-PUC-Minas-PMGES-TI",
        template=Template(
            owner="ICEI-PUC-Minas-PMGES-TI",
            repositorio="TI-ES-GenericTemplate"
        ),
        templates_por_disciplina={
            Disciplina.TI1: Template(
                owner="ICEI-PUC-Minas-PMGES-TI",
                repositorio="ti1-es-template-repository"
            ),
        }
    ),
    "Lourdes": Campus(
        sigla="plf",
        nome="Lourdes",
        organizacao="ICEI-PUC-Minas-PPLES-TI",
        template=Template(
            owner="ICEI-PUC-Minas-PPLES-TI",
            repositorio="TI-ES-GenericTemplate"
        ),
        templates_por_disciplina={
            Disciplina.TI1: Template(
                owner="ICEI-PUC-Minas-PPLES-TI",
                repositorio="ti1-es-template-repository"
            ),
        }
    ),
}
"""Campi disponíveis, indexados pelo nome exibido na interface."""


def listar_nomes_campi() -> List[str]:
    """
    Retorna os nomes dos campi cadastrados, em ordem alfabética.

    Returns:
        List[str]: Nomes dos campi disponíveis para seleção.
    """
    return sorted(CAMPI.keys())


def obter_campus(nome: str) -> Campus:
    """
    Obtém um campus a partir do seu nome.

    Args:
        nome (str): Nome do campus (ex: "Lourdes").

    Returns:
        Campus: Instância correspondente ao nome informado.

    Raises:
        KeyError: Se o campus não estiver cadastrado.
    """
    return CAMPI[nome]
