# História 03 - Criar o repositório na organização do campus

**Como** professor de uma disciplina de Trabalho Interdisciplinar,  
**Eu quero** criar o repositório da equipe na organização do GitHub com um clique  
**Para que** eu não precise criar os repositórios manualmente, um a um, no início de cada semestre.

---

## Critérios de Aceitação

- O repositório deve ser criado na organização correspondente ao campus selecionado.
- O sistema deve verificar se já existe um repositório com o mesmo nome antes de criá-lo e informar o professor caso exista.
- Deve ser possível definir se o repositório será público ou privado e se será criado com um README inicial.
- A URL do repositório criado deve ser exibida como um link.
- Erros de token inválido, falta de permissão e falha na criação devem ser exibidos em mensagens compreensíveis.
- Os repositórios criados durante a sessão devem ser listados e exportáveis em `.csv`.
- Nenhum repositório existente pode ser alterado ou removido pelo sistema.

---

## Tarefas Técnicas

- [ ] Implementar a autenticação na API do GitHub por token pessoal, lido do `.env` ou informado na interface.
- [ ] Implementar a consulta que verifica a existência de um repositório na organização.
- [ ] Implementar a criação do repositório via `POST /orgs/{org}/repos`.
- [ ] Tratar os códigos de erro da API (401, 403, 404 e 422) com mensagens específicas.
- [ ] Registrar os repositórios criados na sessão e permitir a exportação em `.csv`.

---
