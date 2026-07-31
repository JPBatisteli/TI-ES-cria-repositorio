# História 02 - Gerar o nome padronizado do repositório

**Como** professor de uma disciplina de Trabalho Interdisciplinar,  
**Eu quero** informar o código da disciplina e o nome do repositório e visualizar o nome final antes de criá-lo  
**Para que** o repositório siga o padrão de nomenclatura adotado e seja reconhecido nos catálogos de TI e na geração de certificados.

---

## Critérios de Aceitação

- Deve ser possível informar o código da disciplina e o nome do repositório.
- O nome final deve seguir o padrão `<sigla_campus>-es-<ano>-<semestre>-<disciplina>-<código_disciplina>-<nome_repositório>`.
- O nome informado deve ser convertido automaticamente: sem acentuação, em letras minúsculas e com hífens no lugar de espaços e pontuação.
- A prévia do nome final deve ser exibida antes da criação.
- O sistema deve rejeitar código da disciplina não numérico e nome de repositório vazio ou sem caracteres alfanuméricos.
- O sistema deve rejeitar nomes que ultrapassem o limite de 100 caracteres do GitHub.
- O botão de criação deve permanecer desabilitado enquanto o código da disciplina e o nome do repositório não forem informados.

---

## Tarefas Técnicas

- [ ] Implementar a conversão do nome informado em slug.
- [ ] Implementar a montagem do nome padronizado a partir dos dados informados.
- [ ] Implementar a validação dos campos e do nome gerado.
- [ ] Reaproveitar a expressão regular do padrão institucional para validar o nome final.
- [ ] Exibir a prévia do nome e da URL do repositório na interface.
- [ ] Cobrir as regras de nomenclatura e validação com testes automatizados.

---
