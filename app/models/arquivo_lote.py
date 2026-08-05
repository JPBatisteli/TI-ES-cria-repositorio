from dataclasses import dataclass, field
from typing import List, Optional
import re
import unicodedata

from app.models.aluno import Aluno
from app.models.campus import Campus
from app.models.disciplina import Disciplina
from app.models.novo_repositorio import NovoRepositorio
from app.utils import github_utils

# Rótulos aceitos no arquivo, já normalizados (sem acento e em minúsculas).
# Cada rótulo reconhecido é mapeado para o campo correspondente.
ROTULOS = {
    "ti": "disciplina",
    "disciplina": "disciplina",
    "codigo": "codigo",
    "codigo da disciplina": "codigo",
    "repositorio": "repositorio",
    "grupo": "grupo",
    "equipe": "grupo",
    "membros": "membros",
    "alunos": "membros",
}

# Separadores aceitos entre os nomes de usuário na linha de membros.
SEPARADOR_MEMBROS = re.compile(r"[,;]")


def _normalizar(texto: str) -> str:
    """
    Normaliza um rótulo para comparação, removendo acentos e maiúsculas.

    Args:
        texto (str): Rótulo lido do arquivo (ex: "Repositório").

    Returns:
        str: Rótulo normalizado (ex: "repositorio").
    """
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = sem_acento.encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.lower().split())


@dataclass
class GrupoLote:
    """
    Representa um grupo lido do arquivo de criação em lote.

    Attributes:
        nome_repositorio (str): Nome do repositório informado pelo professor.
        nome_grupo (str): Nome do grupo, usado como nome da equipe no GitHub.
        membros (List[Aluno]): Alunos do grupo.
        linha (int): Linha do arquivo em que o grupo começa, usada nas mensagens de erro.
    """
    nome_repositorio: str
    nome_grupo: str = ""
    membros: List[Aluno] = field(default_factory=list)
    linha: int = 0

    @property
    def avisos(self) -> List[str]:
        """
        Retorna os problemas que não impedem a criação, mas merecem atenção.

        Returns:
            List[str]: Avisos sobre o grupo (ex: ausência de membros).
        """
        avisos = []

        if not self.nome_grupo:
            avisos.append("Grupo sem nome — a equipe receberá o nome do repositório.")
        if not self.membros:
            avisos.append("Grupo sem membros — nenhum aluno será adicionado.")

        invalidos = [aluno.username for aluno in self.membros if not aluno.valido]
        if invalidos:
            avisos.append(f"Nomes de usuário inválidos: {', '.join(invalidos)}.")

        return avisos


@dataclass
class ArquivoLote:
    """
    Representa o conteúdo de um arquivo de criação em lote.

    O arquivo começa com um cabeçalho informando a disciplina e o código da turma,
    seguido de um bloco por grupo. Cada bloco traz o nome do repositório, o nome do
    grupo e os nomes de usuário dos membros.

    Exemplo::

        TI: TI1
        Codigo: 2401100

        Repositorio: Adota Pet
        Grupo: Grupo 1
        Membros: ana-souza, bruno-lima

    Attributes:
        disciplina (Optional[Disciplina]): Disciplina informada no cabeçalho.
        codigo_disciplina (str): Código da turma informado no cabeçalho.
        grupos (List[GrupoLote]): Grupos lidos do arquivo.
        erros (List[str]): Problemas que impedem o processamento do arquivo.
    """
    disciplina: Optional[Disciplina] = None
    codigo_disciplina: str = ""
    grupos: List[GrupoLote] = field(default_factory=list)
    erros: List[str] = field(default_factory=list)

    @property
    def valido(self) -> bool:
        """Indica se o arquivo pode ser processado."""
        return not self.erros

    @property
    def total_alunos(self) -> int:
        """Retorna a quantidade de alunos somando todos os grupos."""
        return sum(len(grupo.membros) for grupo in self.grupos)

    @classmethod
    def de_texto(cls, conteudo: str) -> "ArquivoLote":
        """
        Interpreta o conteúdo de um arquivo de criação em lote.

        Linhas vazias e linhas iniciadas por '#' são ignoradas. Um novo grupo começa
        a cada linha 'Repositorio:', de modo que a separação por linhas em branco é
        opcional.

        Args:
            conteudo (str): Conteúdo do arquivo.

        Returns:
            ArquivoLote: Instância com os grupos lidos e os erros encontrados.
        """
        arquivo = cls()
        grupo_atual: Optional[GrupoLote] = None

        for numero, linha in enumerate(conteudo.splitlines(), start=1):
            texto = linha.strip()

            if not texto or texto.startswith("#"):
                continue

            if ":" not in texto:
                arquivo.erros.append(
                    f"Linha {numero}: esperado o formato 'Rótulo: valor', mas foi lido '{texto}'."
                )
                continue

            rotulo, valor = texto.split(":", 1)
            campo = ROTULOS.get(_normalizar(rotulo))
            valor = valor.strip()

            if campo is None:
                arquivo.erros.append(f"Linha {numero}: rótulo desconhecido '{rotulo.strip()}'.")
                continue

            if campo == "repositorio":
                grupo_atual = GrupoLote(nome_repositorio=valor, linha=numero)
                arquivo.grupos.append(grupo_atual)
            elif campo == "disciplina":
                arquivo._ler_disciplina(valor, numero)
            elif campo == "codigo":
                arquivo.codigo_disciplina = valor
            elif grupo_atual is None:
                arquivo.erros.append(
                    f"Linha {numero}: '{rotulo.strip()}' foi informado antes de qualquer "
                    "linha 'Repositorio:'."
                )
            elif campo == "grupo":
                grupo_atual.nome_grupo = valor
            elif campo == "membros":
                grupo_atual.membros.extend(cls._ler_membros(valor))

        arquivo._validar()

        return arquivo

    def _ler_disciplina(self, valor: str, numero: int):
        """Interpreta a disciplina informada no cabeçalho."""
        try:
            self.disciplina = Disciplina[valor.strip().upper()]
        except KeyError:
            self.erros.append(
                f"Linha {numero}: disciplina '{valor}' não reconhecida. "
                f"Use uma entre {', '.join(Disciplina.listar_rotulos())}."
            )

    @staticmethod
    def _ler_membros(valor: str) -> List[Aluno]:
        """Interpreta a lista de nomes de usuário separados por vírgula ou ponto e vírgula."""
        nomes = [nome.strip() for nome in SEPARADOR_MEMBROS.split(valor)]
        return [Aluno.de_texto(nome) for nome in nomes if nome.strip()]

    def _validar(self):
        """Valida o cabeçalho e a consistência entre os grupos lidos."""
        if self.disciplina is None and not any("disciplina" in erro for erro in self.erros):
            self.erros.append("Informe a disciplina no cabeçalho, na linha 'TI:'.")

        if not self.codigo_disciplina:
            self.erros.append("Informe o código da disciplina no cabeçalho, na linha 'Codigo:'.")
        elif not github_utils.validar_codigo_disciplina(self.codigo_disciplina):
            self.erros.append(
                f"O código da disciplina ('{self.codigo_disciplina}') deve conter apenas dígitos."
            )

        if not self.grupos:
            self.erros.append("Nenhum grupo encontrado. Cada grupo começa numa linha 'Repositorio:'.")

        self._validar_nomes_dos_grupos()

    def _validar_nomes_dos_grupos(self):
        """Verifica nomes de repositório vazios ou repetidos entre os grupos."""
        vistos = {}

        for grupo in self.grupos:
            if not grupo.nome_repositorio:
                self.erros.append(f"Linha {grupo.linha}: nome do repositório vazio.")
                continue

            chave = github_utils.gerar_slug(grupo.nome_repositorio)

            if not chave:
                self.erros.append(
                    f"Linha {grupo.linha}: o nome '{grupo.nome_repositorio}' não gera um "
                    "nome de repositório válido."
                )
            elif chave in vistos:
                self.erros.append(
                    f"Linha {grupo.linha}: o repositório '{grupo.nome_repositorio}' repete "
                    f"o da linha {vistos[chave]}."
                )
            else:
                vistos[chave] = grupo.linha

    def montar_solicitacoes(self, campus: Campus, privado: bool = True) -> List[NovoRepositorio]:
        """
        Converte os grupos lidos em solicitações de criação de repositório.

        Cada grupo dá origem a um repositório com equipe própria, nomeada conforme o
        nome do grupo informado no arquivo.

        Args:
            campus (Campus): Campus selecionado pelo professor.
            privado (bool): Indica se os repositórios devem ser criados como privados.

        Returns:
            List[NovoRepositorio]: Solicitações prontas para serem criadas.
        """
        return [
            NovoRepositorio(
                campus=campus,
                disciplina=self.disciplina,
                codigo_disciplina=self.codigo_disciplina,
                nome_projeto=grupo.nome_repositorio,
                privado=privado,
                alunos=list(grupo.membros),
                criar_equipe=True,
                nome_equipe_personalizado=grupo.nome_grupo
            )
            for grupo in self.grupos
        ]
