from dataclasses import dataclass, field
from typing import Dict, List
import re

from app.models.aluno import Aluno

# Separadores aceitos quando mais de um nome de usuário aparece na mesma linha.
SEPARADOR_DE_USUARIOS = re.compile(r"[,;]")


@dataclass
class ListaDeUsuarios:
    """
    Representa o conteúdo de um arquivo com nomes de usuário do GitHub.

    O formato é deliberadamente mínimo: um nome de usuário por linha. Linhas vazias e
    linhas iniciadas por '#' são ignoradas, o que permite comentar a turma no topo do
    arquivo.

    Exemplo::

        # Turma de TI1 - manhã
        ana-souza
        bruno-lima

    Attributes:
        alunos (List[Aluno]): Alunos lidos, sem repetições.
        erros (List[str]): Problemas que impedem o processamento do arquivo.
        avisos (List[str]): Problemas que não impedem o processamento.
    """
    alunos: List[Aluno] = field(default_factory=list)
    erros: List[str] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)

    @property
    def valido(self) -> bool:
        """Indica se o arquivo pode ser processado."""
        return not self.erros

    @property
    def invalidos(self) -> List[str]:
        """Retorna os nomes de usuário que não respeitam as regras do GitHub."""
        return [aluno.username for aluno in self.alunos if not aluno.valido]

    @classmethod
    def de_texto(cls, conteudo: str) -> "ListaDeUsuarios":
        """
        Interpreta o conteúdo de um arquivo de nomes de usuário.

        Nomes repetidos são mantidos uma única vez e reportados como aviso: repetir um
        aluno não causa dano, mas costuma indicar erro na montagem da lista.

        Args:
            conteudo (str): Conteúdo do arquivo.

        Returns:
            ListaDeUsuarios: Instância com os alunos lidos e os problemas encontrados.
        """
        lista = cls()
        primeira_ocorrencia: Dict[str, int] = {}
        repetidos = []

        for numero, linha in enumerate(conteudo.splitlines(), start=1):
            texto = linha.strip()

            if not texto or texto.startswith("#"):
                continue

            for nome in SEPARADOR_DE_USUARIOS.split(texto):
                if not nome.strip():
                    continue

                aluno = Aluno.de_texto(nome)

                if not aluno.username:
                    continue

                chave = aluno.username_normalizado

                if chave in primeira_ocorrencia:
                    repetidos.append(f"'{aluno.username}' (linha {numero})")
                    continue

                primeira_ocorrencia[chave] = numero
                lista.alunos.append(aluno)

        if repetidos:
            lista.avisos.append(
                f"{len(repetidos)} nome(s) repetido(s), considerados uma única vez: "
                f"{', '.join(repetidos)}."
            )

        if not lista.alunos:
            lista.erros.append(
                "Nenhum nome de usuário encontrado. O arquivo deve trazer um por linha."
            )

        return lista
