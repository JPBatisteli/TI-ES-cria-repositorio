# Requisitos do Sistema: Criador de Repositórios de TI

## Requisitos Funcionais (RF)

---

- **RF01.** O sistema deve permitir que o professor selecione o campus em que está lecionando.
- **RF02.** O sistema deve determinar a organização do GitHub em que o repositório será criado a partir do campus selecionado.
- **RF03.** O sistema deve permitir que o professor selecione a disciplina de Trabalho Interdisciplinar, de TI1 a TI6.
- **RF04.** O sistema deve determinar o ano e o semestre letivos a partir da data corrente, sem permitir que o professor os altere, considerando que o 1º semestre vai de 1 de janeiro a 10 de julho e o 2º, de 11 de julho a 31 de dezembro.
- **RF04.1.** O sistema deve exibir o período letivo em vigor e a regra que o determina.
- **RF04.2.** O sistema deve rejeitar solicitações cujo ano e semestre não correspondam ao período letivo em vigor, ainda que informados fora da interface.
- **RF05.** O sistema deve permitir que o professor informe o código da disciplina.
- **RF06.** O sistema deve permitir que o professor informe o nome do repositório.
- **RF07.** O sistema deve montar o nome do repositório conforme o padrão de nomenclatura adotado:

  `<sigla_campus>-es-<ano>-<semestre>-<disciplina>-<código_disciplina>-<nome_repositório>`

- **RF08.** O sistema deve converter o nome informado pelo professor em um slug compatível com o GitHub, removendo acentuação, aplicando letras minúsculas e substituindo espaços e pontuação por hífens.
- **RF09.** O sistema deve exibir a prévia do nome do repositório antes da criação.
- **RF10.** O sistema deve validar os dados informados, rejeitando:

  * Código da disciplina vazio ou com caracteres não numéricos
  * Nome do repositório vazio ou sem caracteres alfanuméricos
  * Ano fora do intervalo aceito e semestre diferente de 1 ou 2
  * Nome gerado fora do padrão ou acima do limite de 100 caracteres do GitHub

- **RF11.** O sistema deve verificar se já existe um repositório com o mesmo nome na organização antes de criá-lo.
- **RF12.** O sistema deve criar o repositório na organização selecionada por meio da API do GitHub.
- **RF13.** O sistema deve permitir definir a visibilidade do repositório (público ou privado) e a criação de um README inicial.
- **RF14.** O sistema deve exibir a URL do repositório criado.
- **RF15.** O sistema deve exibir mensagens de erro compreensíveis quando a criação não for concluída (token inválido, falta de permissão, repositório duplicado).
- **RF16.** O sistema deve manter a lista dos repositórios criados durante a sessão e permitir a sua exportação em `.csv`.
- **RF17.** O sistema deve carregar os membros da organização do campus, excluindo os proprietários, para auxiliar a seleção dos alunos.
- **RF18.** O sistema deve permitir que o professor busque os alunos pelo nome de usuário, filtrando a lista à medida que digita, e também informe nomes de usuário que não constem na lista.
- **RF19.** O sistema deve verificar, para cada aluno informado, se ele pertence à organização do campus antes de conceder acesso.
- **RF20.** O sistema deve conceder permissão de escrita aos alunos que pertencem à organização.
- **RF21.** O sistema deve informar ao professor, individualmente por aluno, o desfecho da concessão de acesso, distinguindo acesso concedido, convite pendente, aluno fora da organização e nome de usuário inválido.
- **RF22.** O sistema deve prosseguir com os demais alunos quando a adição de um deles falhar, mantendo o repositório criado.
- **RF23.** O sistema deve permitir que o professor opte por criar uma equipe no GitHub para o repositório.
- **RF24.** O sistema deve permitir que o professor informe o nome da equipe e, quando o campo estiver vazio, derivá-lo do nome do repositório.
- **RF24.1.** O sistema deve exibir, antes da criação, o nome que será usado para a equipe e a sua origem (informado ou derivado).
- **RF24.2.** A equipe deve ser criada com privacidade `closed`.
- **RF25.** A equipe criada deve receber permissão de administração sobre o repositório.
- **RF26.** Quando a equipe for criada, os alunos devem ser adicionados a ela em vez de receberem acesso individual.
- **RF27.** O sistema deve manter o repositório criado e conceder acesso individual aos alunos caso a criação da equipe falhe, informando o motivo da falha.
- **RF28.** O sistema deve oferecer, em aba própria, a criação de vários repositórios a partir de um arquivo `.txt`.
- **RF29.** O arquivo deve conter um cabeçalho com a disciplina e o código da turma, seguido de um bloco por grupo com o nome do repositório, o nome do grupo e os nomes de usuário dos membros.
- **RF30.** O sistema deve reportar os erros de formato do arquivo indicando o número da linha, impedindo o processamento.
- **RF31.** O sistema deve exibir uma prévia com os nomes finais dos repositórios, as equipes e a contagem de alunos antes de criar qualquer coisa.
- **RF32.** O sistema deve sinalizar, na prévia, os avisos que não impedem a criação (grupo sem nome, sem membros ou com nome de usuário inválido).
- **RF33.** Cada grupo do arquivo deve originar um repositório e uma equipe com o nome do grupo, administradora do repositório.
- **RF34.** O sistema deve prosseguir com os demais repositórios quando a criação de um deles falhar, e exibir o progresso durante a operação.
- **RF35.** O sistema deve reunir, ao final, os alunos que não receberam acesso e permitir a exportação do resultado em `.csv`.
- **RF36.** O sistema deve verificar, ao receber o arquivo e sem criar nada, se o nome de cada repositório está disponível na organização.
- **RF37.** O sistema deve verificar se o nome de cada equipe está disponível na organização.
- **RF38.** O sistema deve verificar cada aluno informado, distinguindo nome de usuário inválido, conta inexistente no GitHub e conta que não pertence à organização.
- **RF39.** O sistema deve habilitar a criação em lote somente quando nenhum grupo apresentar impedimento.
- **RF40.** O sistema deve exibir os impedimentos por grupo e permitir que a verificação seja refeita sob demanda.
- **RF41.** O sistema deve sugerir a conferência do campus quando nenhum aluno do arquivo pertencer à organização selecionada.
- **RF42.** O sistema deve permitir definir a visibilidade dos repositórios criados em lote, valendo para todos os grupos do arquivo, adotando repositórios privados como padrão.
- **RF43.** O sistema deve identificar as respostas em que o GitHub recusa a requisição por excesso de chamadas, distinguindo-as das recusas por falta de permissão.
- **RF44.** O sistema deve repetir automaticamente a requisição recusada por excesso de chamadas, aguardando o tempo indicado pelo cabeçalho `Retry-After` ou, na sua ausência, 30 segundos.
- **RF45.** O sistema deve informar o professor durante a espera, indicando os segundos restantes e a tentativa em curso.
- **RF46.** O sistema deve desistir após três tentativas, exibindo mensagem que esclareça tratar-se de limite de requisições, e não de permissão.
- **RF47.** O sistema deve espaçar as requisições de escrita de modo a manter o ritmo abaixo do limite do GitHub, sem afetar as consultas.
- **RF48.** O sistema deve registrar o resultado de cada repositório assim que ele é concluído, preservando o registro caso a execução seja interrompida.
- **RF49.** O sistema deve informar quantos repositórios chegaram a ser processados quando a criação em lote for interrompida antes do fim.
- **RF50.** O sistema deve permitir retomar um lote interrompido a partir do mesmo arquivo, sem exigir a sua edição.
- **RF51.** Na retomada, os grupos cujo repositório já existe devem ser ignorados sem bloquear a criação dos demais.
- **RF52.** Os problemas que exigem correção — nome de usuário inválido, conta inexistente, aluno fora da organização e equipe já em uso sem repositório correspondente — devem continuar bloqueando a criação.
- **RF53.** O sistema deve sinalizar os grupos cujo repositório existe sem a equipe correspondente, por indicarem criação interrompida no meio do grupo.

## Requisitos Não Funcionais (RNF)

---

- **RNF01.** O sistema deve utilizar autenticação segura para acesso à API do GitHub, por meio de token pessoal.
- **RNF02.** O token não deve ser versionado, sendo lido do arquivo `.env` ou informado em campo protegido na interface.
- **RNF03.** O sistema não deve alterar ou remover repositórios existentes, nem alterar a associação dos alunos à organização.
- **RNF09.** A listagem dos membros da organização deve ser mantida em cache durante a sessão, evitando recarregamento a cada interação da interface.
- **RNF04.** O sistema deve ser multiplataforma (executável em ambientes Linux, Windows ou macOS).
- **RNF05.** As regras de nomenclatura devem ser compatíveis com as verificadas pela ferramenta Verifica Citation, garantindo que os repositórios criados sejam reconhecidos nos catálogos de TI.
- **RNF06.** O cadastro de campi e organizações deve ser alterável em um único ponto do código, sem alteração da interface.
- **RNF07.** As regras de nomenclatura e validação devem ser cobertas por testes automatizados.
- **RNF08.** O código-fonte do sistema deve estar versionado em repositório Git e seguir boas práticas de codificação e documentação.
