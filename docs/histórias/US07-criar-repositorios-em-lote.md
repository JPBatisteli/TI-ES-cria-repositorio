# História 07 - Criar repositórios em lote

**Como** professor de uma disciplina de Trabalho Interdisciplinar,  
**Eu quero** criar os repositórios de todos os grupos da turma a partir de um arquivo  
**Para que** eu não precise repetir o mesmo formulário dezenas de vezes no início de cada semestre.

---

## Critérios de Aceitação

- A criação em lote deve ficar numa aba própria, separada da criação individual.
- Deve ser possível enviar um arquivo `.txt` com a disciplina, o código da turma e um bloco por grupo.
- O arquivo deve informar, por grupo, o nome do repositório, o nome do grupo e os nomes de usuário dos membros.
- Cada grupo deve gerar um repositório e uma equipe com o nome do grupo, administradora desse repositório.
- O campus deve ser escolhido na aba, e não no arquivo, por determinar a organização.
- Erros de formato devem impedir o processamento e ser listados com o número da linha.
- Avisos que não impedem a criação devem ser exibidos na prévia.
- A prévia deve mostrar os nomes finais dos repositórios antes de qualquer criação.
- Ao receber o arquivo, os dados devem ser verificados no GitHub sem que nada seja criado.
- A verificação deve cobrir a disponibilidade do nome do repositório, a disponibilidade do nome da equipe e a existência de cada aluno na organização.
- A criação só deve ser habilitada quando nenhum grupo apresentar impedimento.
- Deve ser possível refazer a verificação sob demanda.
- A falha na criação de um repositório não deve interromper os demais.
- O progresso deve ser exibido durante a criação.
- O resultado deve reunir, num único lugar, os alunos que ficaram sem acesso.
- O resultado deve ser exportável em `.csv`.

---

## Tarefas Técnicas

- [ ] Modelar a leitura do arquivo, com rótulos, sinônimos e mensagens por linha.
- [ ] Validar cabeçalho, nomes repetidos e nomes que não geram repositório válido.
- [ ] Converter os grupos lidos em solicitações de criação.
- [ ] Implementar a criação em sequência, com retorno de progresso.
- [ ] Extrair a barra lateral, que passa a ser comum às abas.
- [ ] Criar a aba de lote com envio do arquivo, prévia, progresso e resultado.
- [ ] Disponibilizar um modelo de arquivo para download.
- [ ] Implementar a verificação prévia, reaproveitando as listas de membros e equipes.
- [ ] Distinguir conta inexistente de conta fora da organização (`GET /users/{username}`).
- [ ] Guardar o resultado da verificação enquanto o arquivo e o campus não mudarem.
- [ ] Cobrir a leitura do arquivo e a criação em lote com testes automatizados.

---

## Retomada

Um lote interrompido é retomado enviando o mesmo arquivo novamente. Grupos cujo
repositório já existe são dados por concluídos e ignorados; os problemas que exigem
correção continuam bloqueando. Repositórios existentes **sem equipe** são sinalizados
à parte, por indicarem interrupção no meio do grupo — nesse caso os alunos podem não
ter recebido acesso, e a conferência é feita pela aba de criação individual.

---

## Fora do Escopo

Alunos que não pertencem à organização continuam apenas reportados, como definido na
[US04](US04-adicionar-alunos-ao-repositorio.md). O arquivo trata de uma turma por vez:
a disciplina e o código valem para todos os grupos, e turmas diferentes exigem arquivos
diferentes.

---
