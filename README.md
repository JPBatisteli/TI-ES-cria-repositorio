# 📦 Criador de Repositórios de TI

Ferramenta com interface gráfica para que os professores das disciplinas de Trabalho Interdisciplinar (TI) criem os repositórios das equipes de alunos no GitHub, já dentro da organização correta e seguindo o padrão de nomenclatura da Engenharia de Software - PUC Minas.

---

## 🎯 Objetivo

Evitar erros na criação manual dos repositórios dos TIs, garantindo que:

- O repositório seja criado na organização do campus correto
- O nome siga o padrão `<campus>-es-<ano>-<semestre>-<ti>-<código_disciplina>-<nome_repositório>`
- Não sejam criados repositórios duplicados na organização

O padrão de nomenclatura é o mesmo verificado pela ferramenta [Verifica Citation](../TI-ES-verifica-citation), o que mantém os catálogos de TI e a geração de certificados consistentes.

---

## 🏷️ Padrão de nomenclatura

```
<sigla_campus>-es-<ano>-<semestre>-<disciplina>-<código_disciplina>-<nome_repositório>
```

| Parte                | Origem                                        | Exemplo           |
|----------------------|-----------------------------------------------|-------------------|
| `sigla_campus`       | Campus selecionado                            | `pmg`             |
| `es`                 | Curso (fixo)                                  | `es`              |
| `ano`                | Ano letivo, determinado pela data atual        | `2025`            |
| `semestre`           | Semestre letivo, determinado pela data atual   | `1`               |
| `disciplina`         | TI selecionado (TI1 a TI6)                    | `ti2`             |
| `código_disciplina`  | Código informado pelo professor               | `3687100`         |
| `nome_repositório`   | Nome informado pelo professor, convertido em slug | `brecho-re-use` |

Exemplo final: `pmg-es-2025-1-ti2-3687100-brecho-re-use`

O nome informado é convertido automaticamente: acentos são removidos, letras são
convertidas para minúsculas e espaços e pontuação viram hífens. Ou seja,
`Brechó Re-Use` resulta em `brecho-re-use`.

---

## 📅 Período letivo

O ano e o semestre **não são escolhidos pelo professor**: são determinados pela data em
que a aplicação é usada, para impedir a criação de repositórios em semestres já
encerrados ou ainda não iniciados.

| Período | Intervalo |
|---|---|
| 1º semestre | 1 de janeiro a **10 de julho** |
| 2º semestre | **11 de julho** a 31 de dezembro |

Os campos aparecem desabilitados na interface, com o período em vigor indicado abaixo
deles. A regra está em [`app/models/periodo_letivo.py`](app/models/periodo_letivo.py) e
é validada de novo no modelo antes da criação, de modo que a restrição não dependa
apenas da interface.

---

## 🏫 Campi e organizações

| Campus                | Sigla | Organização no GitHub       | Repositório-modelo          |
|-----------------------|-------|-----------------------------|-----------------------------|
| Coração Eucarístico   | `pmg` | `ICEI-PUC-Minas-PMGES-TI`   | `TI-ES-GenericTemplate`     |
| Lourdes               | `plf` | `ICEI-PUC-Minas-PPLES-TI`   | `TI-ES-GenericTemplate`     |

Novos campi são cadastrados em [`app/models/campus.py`](app/models/campus.py), no dicionário `CAMPI`.

---

## 📁 Repositório-modelo

Os repositórios **não nascem vazios**: são gerados a partir do modelo da organização do
campus, via `POST /repos/{owner}/{modelo}/generate`. Cada campus tem o seu, na própria
organização, e a escolha é automática — o professor não seleciona nada.

O que isso implica:

- O repositório nasce com a estrutura de arquivos do modelo, num **commit inicial único**
- Histórico, issues e pull requests do modelo **não** são copiados
- Não há opção de README inicial: o conteúdo vem sempre do modelo

Os repositórios também são **sempre privados**. Nem a visibilidade nem a origem do
conteúdo são escolhas do professor — são o padrão institucional, fixado no código.

O modelo precisa estar marcado como template no GitHub (*Settings → Template repository*).
Na criação em lote isso é verificado **uma vez por lote**, antes de qualquer criação: se
o modelo não existir ou não estiver marcado, nada é criado e o motivo aparece na tela.

Um campus sem modelo configurado (`template=None`) volta a criar repositórios vazios,
respeitando a opção de README.

---

## 🖥️ Tecnologias

- [Streamlit](https://streamlit.io) — interface web local
- [API REST do GitHub](https://docs.github.com/rest) — criação dos repositórios
- [requests](https://requests.readthedocs.io) — chamadas HTTP
- [pandas](https://pandas.pydata.org) — exportação da lista de repositórios criados
- [pytest](https://docs.pytest.org) — testes automatizados

---

## 🚀 Como executar

### 1. Clone o repositório

```bash
git clone https://github.com/central-es/cria-repositorio.git
cd cria-repositorio
```

### 2. Crie o ambiente virtual e instale as dependências

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure o token do GitHub

```bash
cp .env.example .env
```

Edite o arquivo `.env` e informe o seu token pessoal:

```
GITHUB_TOKEN=ghp_seu_token_aqui
```

O token precisa ter o escopo `repo` e o usuário precisa ter permissão para criar
repositórios na organização do campus. Alternativamente, o token pode ser
informado diretamente na barra lateral da aplicação.

### 4. Execute a aplicação

```bash
streamlit run app/main.py
```

### 5. Execute os testes

```bash
pytest
```

---

## 🐳 Execução com Docker

Alternativa a instalar Python e dependências na máquina — útil para distribuir a
aplicação aos professores.

```bash
docker compose up --build
```

A aplicação fica em `http://localhost:8501`.

### O token

**O token nunca é embutido na imagem.** O `.dockerignore` exclui `.env` e `.env.example`
justamente para isso. Há duas formas de informá-lo:

```bash
# 1. Pela variável de ambiente de quem executa
GITHUB_TOKEN=ghp_seu_token docker compose up

# 2. Sem variável nenhuma: a aplicação sobe e pede o token na barra lateral
docker compose up
```

Se preferir usar um arquivo `.env` já existente, monte-o em tempo de execução em vez
de copiá-lo para a imagem:

```bash
docker run --rm -p 8501:8501 -v "$(pwd)/.env:/app/.env:ro" ti-es-cria-repositorio
```

### Sem Docker Compose

```bash
docker build -t ti-es-cria-repositorio .
docker run --rm -p 8501:8501 -e GITHUB_TOKEN=ghp_seu_token ti-es-cria-repositorio
```

### Detalhes da imagem

- Base `python:3.11-slim` — a aplicação usa sintaxe de anotações que exige Python 3.10+
- Executa como usuário sem privilégios (`streamlit`, uid 1000)
- A pasta `docs/` acompanha a imagem porque a aba de lote lê dela o arquivo de exemplo
- `tests/` fica de fora da imagem de execução
- Verificação de saúde pelo endpoint `/_stcore/health` do próprio Streamlit

---

## 📋 Funcionalidades

- Seleção do campus, que define a organização do GitHub e a sigla do repositório
- Seleção da disciplina de TI (TI1 a TI6), do ano e do semestre
- Inserção do código da disciplina e do nome do repositório
- Prévia do nome padronizado antes da criação
- Validação dos dados informados e do nome gerado
- Verificação de repositório já existente na organização
- Criação do repositório (público ou privado, com ou sem README inicial)
- Seleção dos alunos da equipe, com busca entre os membros da organização
- Concessão de permissão de escrita aos alunos, com retorno individual por aluno
- Lista dos repositórios criados na sessão, exportável em `.csv`

---

## 👥 Adição dos alunos

Ao criar o repositório, os alunos selecionados recebem **permissão de escrita** (`push`).

O campo de alunos carrega os membros da organização do campus e filtra conforme o
professor digita. A listagem usa `GET /orgs/{org}/members?role=member`, que exclui os
proprietários — como os professores são owners, o resultado corresponde aos alunos.
Também é possível digitar um nome de usuário que não esteja na lista.

A opção **"Incluir os proprietários da organização na lista"** troca o filtro para
`role=all`, trazendo também os professores. É útil para testar o fluxo com contas
próprias. Em uso normal ela não é necessária: proprietários da organização já possuem
acesso de administrador a todos os repositórios, e adicioná-los como colaboradores não
altera essa permissão.

Antes de conceder o acesso, a aplicação verifica se o aluno pertence à organização.
Cada aluno recebe um desfecho próprio:

| Situação | Significado |
|---|---|
| Acesso de escrita concedido | O aluno já é membro da organização e passou a ter acesso imediato |
| Convite enviado | O GitHub criou um convite, que o aluno precisa aceitar |
| Não faz parte da organização | Caso típico de calouro ainda não cadastrado, ou de nome de usuário incorreto |
| Nome de usuário inválido | O texto informado não respeita as regras de formação do GitHub |

A falha de um aluno não interrompe os demais, e o repositório permanece criado ainda
que nenhum aluno seja adicionado — os que faltarem podem ser incluídos depois.

---

## 🧑‍🤝‍🧑 Criação da equipe

A opção **"Criar uma equipe no GitHub para este repositório"** muda a forma como o
acesso é concedido:

| | Sem equipe (padrão) | Com equipe |
|---|---|---|
| Acesso ao repositório | Colaborador individual | Concedido à equipe |
| Permissão | `push` (escrita) | `admin` (administração) |
| Chamadas por aluno | `PUT .../collaborators/{user}` | `PUT .../teams/{slug}/memberships/{user}` |

O campo **"Nome da equipe (opcional)"** aparece quando a opção é marcada. Deixando-o em
branco, a equipe recebe o **mesmo nome do repositório** — que já é único na organização
por seguir o padrão de nomenclatura. A interface mostra, abaixo do campo e na prévia,
qual nome será usado e se ele foi informado ou derivado.

Ao escolher um nome próprio, lembre-se de que ele precisa ser único na organização:
nomes curtos e genéricos tendem a colidir com equipes de outras turmas ou semestres,
já que as organizações acumulam centenas de times por ano.

A equipe é criada com privacidade `closed`, visível aos membros da organização. Times
`secret` não podem ser aninhados, então essa escolha mantém aberta a possibilidade de
organizar as equipes sob um time da turma.

A verificação de associação à organização continua valendo: alunos que não são membros
não são adicionados à equipe, apenas reportados.

**O professor é removido da equipe ao final.** O GitHub inclui automaticamente como
mantenedor quem cria uma equipe, sem oferecer forma de evitar isso — a documentação é
explícita: *"When you create a new team, you automatically become a team maintainer
without explicitly adding yourself to the optional array of maintainers."* Sem a
remoção, o professor se acumularia nas equipes de todas as turmas, de todos os
semestres.

Isso não lhe custa acesso: proprietários da organização administram todas as equipes,
sejam membros delas ou não. A remoção acontece **depois** de os alunos entrarem, de
modo que, se falhar, o repositório, a equipe e o acesso da equipe já estão prontos — o
professor recebe apenas um aviso.

Se a criação da equipe falhar — por exemplo, se já existir um time com esse nome — o
repositório permanece criado e os alunos recebem **acesso individual com permissão de
escrita**, para que ninguém fique sem acesso. A falha é exibida na tela.

---

## 📚 Criação em lote

A aba **Criação em lote** cria os repositórios de uma turma inteira a partir de um
arquivo `.txt`. Cada grupo do arquivo dá origem a um repositório e a uma equipe com o
nome do grupo, administradora desse repositório.

### Formato do arquivo

O arquivo é lido linha a linha, no formato `Rótulo: valor`. Linhas vazias e linhas
iniciadas por `#` são ignoradas, e **cada grupo começa numa linha `Repositorio:`** —
a separação por linhas em branco é opcional.

```text
Repositorio: Adota Pet
Grupo: Grupo 1
Membros: ana-souza, bruno-lima, carla-dias

Repositorio: Brechó Re-Use
Grupo: Grupo 2
Membros: joao-silva, maria-dev
```

| Rótulo | Sinônimos | Significado |
|---|---|---|
| `Repositorio` | `Repositório` | Nome do projeto — inicia um novo grupo |
| `Grupo` | `Equipe` | Nome da equipe criada no GitHub |
| `Membros` | `Alunos` | Nomes de usuário, separados por vírgula ou ponto e vírgula |

A **turma** — campus, disciplina, turno e código — é escolhida na própria aba, e não no
arquivo. Os códigos vêm de um catálogo, de modo que o professor seleciona entre as
turmas existentes em vez de digitar o código. O ano e o semestre vêm do período letivo
em vigor.

Arquivos no formato antigo continuam sendo aceitos: as linhas `TI:` e `Codigo:` são
ignoradas, com aviso na tela.

A visibilidade também é definida na aba e vale para todos os grupos do arquivo. Os
repositórios do lote são criados **privados por padrão**; a opção pode ser desmarcada
para criá-los públicos.

O arquivo [`docs/exemplo-criacao-em-lote.txt`](docs/exemplo-criacao-em-lote.txt) traz um
exemplo pronto, comentado com as instruções de preenchimento. É o mesmo arquivo
oferecido pelo botão **Baixar modelo comentado** na interface, e os testes garantem que
ele continua válido conforme as regras evoluem.

### Verificação prévia

Ao enviar o arquivo, a aplicação consulta o GitHub e verifica cada grupo **sem criar
nada**. O botão de criação só é habilitado quando não há nenhum impedimento:

| Verificação | Impedimento quando |
|---|---|
| Nome do repositório | Já existe repositório com esse nome na organização |
| Nome da equipe | Já existe equipe com esse nome na organização |
| Alunos | Algum nome de usuário é inválido, não existe no GitHub, ou existe mas não pertence à organização |

A tabela mostra a situação de cada grupo e os impedimentos encontrados. Se **nenhum**
aluno do arquivo pertencer à organização, a aplicação sugere conferir o campus
selecionado — é o sintoma de ter escolhido o campus errado.

A verificação é refeita quando o arquivo ou o campus mudam. O botão **Verificar de
novo** força a reconsulta, útil depois de corrigir algo diretamente no GitHub.

O custo é de uma consulta por repositório mais uma por aluno que não esteja na
organização: as listas de membros e de equipes são carregadas uma única vez, e alunos
repetidos entre grupos são consultados apenas uma vez.

### Limites de requisição do GitHub

O GitHub impõe **80 requisições de escrita por minuto** e 500 por hora. Uma turma
consome `3 × grupos + alunos` escritas — 10 grupos de 6 alunos dão 90, acima do teto
por minuto.

A aplicação lida com isso de duas formas:

**Prevenção.** As requisições de escrita são espaçadas em 0,8 segundo, o que mantém o
ritmo em 75 por minuto — abaixo do teto. O pior caso (10 grupos de 6 alunos, 90
escritas) passa a levar cerca de 1min15 em vez de estourar o limite. As consultas não
são afetadas.

**Reação.** Se ainda assim o limite for atingido, a aplicação **aguarda e repete
automaticamente**: respeita o cabeçalho `Retry-After` devolvido pela API ou, na
ausência dele, espera 30 segundos. São até três tentativas por requisição, com aviso
na tela durante cada espera.

Os resultados são gravados **a cada repositório concluído**, e não ao final. Se a
execução for interrompida — queda de conexão, página recarregada —, o professor
continua enxergando o que já foi criado, com um aviso indicando quantos dos grupos
chegaram a ser processados.

### Retomada de um lote interrompido

Basta **enviar o mesmo arquivo de novo**, sem editá-lo. A verificação distingue duas
situações:

| Situação | Efeito |
|---|---|
| O repositório já existe | O grupo é dado por concluído e **ignorado**, sem bloquear os demais |
| Nome de usuário inválido, conta inexistente, aluno fora da organização, equipe em uso sem repositório correspondente | **Bloqueia** a criação até ser corrigido |

O botão passa a indicar o que resta — *"Criar os 7 repositórios restantes"* — e apenas
os grupos pendentes são enviados.

Um caso merece atenção: se um repositório existe **sem a equipe correspondente**, o
lote provavelmente foi interrompido no meio daquele grupo, e os alunos podem não ter
recebido acesso. Como a retomada ignora repositórios existentes, esses grupos são
sinalizados à parte para conferência pela aba de criação individual.

Como o GitHub usa o mesmo código 403 para excesso de requisições e para falta de
permissão, a distinção é feita pelos cabeçalhos e pela mensagem da resposta — evitando
que o professor investigue o token quando o problema é apenas de ritmo.

### Comportamento

Antes de criar qualquer coisa, a aplicação exibe uma prévia com os nomes finais dos
repositórios, as equipes e a contagem de alunos, além de avisos que não impedem a
criação — grupo sem membros, grupo sem nome ou nome de usuário inválido.

Erros de formato impedem o processamento e são listados com o número da linha:
rótulo desconhecido, linha sem rótulo, disciplina não reconhecida, código não numérico,
repositório repetido, ou membros informados antes do primeiro `Repositorio:`.

Durante a criação, cada repositório é independente: a falha de um não interrompe os
demais. Ao final, o resultado traz o desfecho de cada repositório, uma tabela reunindo
os alunos que ficaram sem acesso e a exportação em `.csv`.

---

## 🗂️ Estrutura do projeto

```
app/
├── main.py                                  # Ponto de entrada da aplicação Streamlit
├── config.py                                # Carregamento das variáveis de ambiente
├── models/
│   ├── aluno.py                             # Aluno e validação do nome de usuário
│   ├── arquivo_lote.py                      # Leitura do arquivo de criação em lote
│   ├── campus.py                            # Campus, siglas e organizações do GitHub
│   ├── disciplina.py                        # Disciplinas de TI (TI1 a TI6)
│   ├── novo_repositorio.py                  # Nome padronizado e regras de validação
│   ├── periodo_letivo.py                    # Período letivo derivado da data
│   ├── resultado_adicao_aluno.py            # Situação da adição de cada aluno
│   ├── resultado_criacao.py                 # Desfecho de uma solicitação de criação
│   └── verificacao_lote.py                  # Verificação prévia do arquivo de lote
├── services/
│   └── github_service.py                    # Comunicação com a API do GitHub
├── controllers/
│   └── criacao_repositorio_controller.py    # Orquestração da criação
├── views/
│   ├── barra_lateral.py                     # Configurações comuns às abas
│   ├── criacao_lote_view.py                 # Aba de criação em lote
│   └── criacao_repositorio_view.py          # Aba de criação individual
└── utils/
    └── github_utils.py                      # Slug, regex e validações do nome
docs/
├── requisitos.md
└── histórias/
tests/
└── test_novo_repositorio.py
```
