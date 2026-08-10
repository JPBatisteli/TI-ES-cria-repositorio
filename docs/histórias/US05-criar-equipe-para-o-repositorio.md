# História 05 - Criar a equipe do repositório

**Como** professor de uma disciplina de Trabalho Interdisciplinar,  
**Eu quero** criar uma equipe no GitHub junto com o repositório e colocar os alunos nela  
**Para que** o acesso da equipe seja gerido num único lugar, em vez de aluno a aluno.

---

## Critérios de Aceitação

- Deve ser possível optar pela criação da equipe no momento da criação do repositório.
- Deve ser possível informar o nome da equipe.
- Quando o nome não for informado, ele deve ser derivado do nome do repositório, garantindo unicidade na organização.
- A interface deve deixar explícito qual nome será usado e se ele foi informado ou derivado.
- A equipe deve ser criada com privacidade `closed`, para permitir aninhamento futuro sob um time da turma.
- A equipe deve receber permissão de administração sobre o repositório.
- Os alunos devem ser adicionados à equipe, e não como colaboradores individuais.
- O professor que cria a equipe deve ser removido dela ao final, já que o GitHub o inclui automaticamente como mantenedor.
- A falha na remoção não deve invalidar a criação, apenas gerar aviso.
- Apenas alunos que já pertencem à organização devem ser adicionados; os demais continuam sendo apenas reportados.
- O nome da equipe a ser criada deve aparecer na prévia, antes da criação.
- Caso a criação da equipe falhe, o repositório deve permanecer criado, o motivo deve ser exibido e os alunos devem receber acesso individual.

---

## Tarefas Técnicas

- [ ] Implementar a criação da equipe (`POST /orgs/{org}/teams`).
- [ ] Criar o campo opcional do nome da equipe, com o nome derivado como sugestão.
- [ ] Implementar a concessão de acesso ao repositório (`PUT /orgs/{org}/teams/{slug}/repos/{org}/{repo}`).
- [ ] Implementar a adição de membros à equipe (`PUT /orgs/{org}/teams/{slug}/memberships/{username}`).
- [ ] Distinguir o estado `active` do estado `pending` na associação.
- [ ] Ramificar o fluxo do controller entre equipe e colaborador individual.
- [ ] Criar a opção na interface e exibir o resultado da criação da equipe.
- [ ] Cobrir as regras com testes automatizados.

---

## Fora do Escopo

Alunos que ainda não pertencem à organização continuam apenas identificados e
reportados, como definido na [US04](US04-adicionar-alunos-ao-repositorio.md). O
aninhamento das equipes sob um time da turma também não faz parte desta história —
a privacidade `closed` apenas mantém essa possibilidade aberta.

---
