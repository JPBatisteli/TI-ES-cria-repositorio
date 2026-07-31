# História 06 - Restringir o período letivo

**Como** coordenador das disciplinas de Trabalho Interdisciplinar,  
**Eu quero** que o ano e o semestre sejam determinados pela data corrente  
**Para que** não sejam criados repositórios em semestres já encerrados ou ainda não iniciados, o que quebraria os catálogos de TI e a geração de certificados.

---

## Critérios de Aceitação

- O ano e o semestre devem ser determinados pela data em que a aplicação é usada.
- O 1º semestre deve compreender 1 de janeiro a 10 de julho.
- O 2º semestre deve compreender 11 de julho a 31 de dezembro.
- Os campos de ano e semestre não devem ser editáveis pelo professor.
- A interface deve exibir o período em vigor e a regra que o determina.
- A restrição deve ser validada no modelo, e não apenas na interface.

---

## Tarefas Técnicas

- [ ] Modelar o período letivo com a regra de corte entre os semestres.
- [ ] Permitir injetar a data de referência, para que a regra seja testável.
- [ ] Substituir os campos editáveis de ano e semestre por campos desabilitados.
- [ ] Validar o período no modelo antes da criação.
- [ ] Cobrir as datas de fronteira com testes automatizados.

---

## Decisão: não permitir o semestre seguinte

A restrição ao período em vigor é deliberada, e não uma limitação a ser removida depois.

Criar repositórios exige conhecer as equipes, e as equipes só são formadas depois que
o semestre começa e as turmas estão constituídas. Preparar repositórios antecipadamente
não seria apenas desnecessário: produziria repositórios sem equipe definida, com nomes
de projeto que ainda não existem.

Por isso o período letivo é derivado da data e não é configurável.

---
