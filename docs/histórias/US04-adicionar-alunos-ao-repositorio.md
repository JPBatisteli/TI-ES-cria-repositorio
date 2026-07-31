# História 04 - Adicionar os alunos ao repositório

**Como** professor de uma disciplina de Trabalho Interdisciplinar,  
**Eu quero** selecionar os alunos da equipe e conceder-lhes acesso ao repositório no momento da criação  
**Para que** a equipe possa começar a trabalhar imediatamente, sem que eu precise adicionar cada aluno manualmente pelo GitHub.

---

## Critérios de Aceitação

- Deve ser possível selecionar os alunos pelo nome de usuário do GitHub.
- A lista de membros da organização do campus deve ser carregada para auxiliar a seleção, filtrando à medida que o professor digita.
- Os proprietários da organização (os professores) não devem aparecer na lista de alunos.
- Deve ser possível informar um nome de usuário que não conste na lista.
- Nomes de usuário repetidos devem ser considerados uma única vez.
- Os alunos que pertencem à organização devem receber permissão de escrita no repositório.
- Os alunos que não pertencem à organização não devem receber acesso, e o professor deve ser informado com orientação sobre o que fazer.
- O desfecho deve ser exibido individualmente por aluno, distinguindo acesso concedido de convite pendente.
- A falha na adição de um aluno não deve impedir a adição dos demais.
- O repositório deve permanecer criado mesmo que nenhum aluno seja adicionado.

---

## Tarefas Técnicas

- [ ] Modelar o aluno e validar o nome de usuário conforme as regras do GitHub.
- [ ] Implementar a listagem paginada dos membros da organização (`GET /orgs/{org}/members?role=member`).
- [ ] Manter a listagem em cache para não recarregar a cada interação da interface.
- [ ] Implementar a verificação de associação do aluno (`GET /orgs/{org}/members/{username}`).
- [ ] Implementar a concessão de acesso (`PUT /repos/{org}/{repo}/collaborators/{username}` com permissão `push`).
- [ ] Distinguir a resposta 201 (convite pendente) da 204 (acesso imediato).
- [ ] Criar o campo de seleção com busca por digitação na interface.
- [ ] Exibir a tabela com o desfecho por aluno.
- [ ] Cobrir as regras com testes automatizados.

---

## Fora do Escopo

O cadastro de alunos que ainda não pertencem à organização — situação esperada entre
calouros de TI1 — não faz parte desta história. A aplicação apenas identifica e reporta
esses casos. A forma de admiti-los (pela organização ou pela própria aplicação) será
definida separadamente.

---
