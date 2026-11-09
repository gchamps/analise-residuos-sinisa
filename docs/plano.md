# Plano de melhorias

Registro do plano de trabalho, do modelo de orquestração e do andamento. Atualizado a cada etapa.

## Etapas

| # | Etapa | Entregas | Status |
|---|---|---|---|
| 0 | Auditoria de base | `tests/` de caracterização (números hoje publicados) e do ETL, `requirements-dev.txt`; auditada, achados médios corrigidos | feito |
| 1 | Fundação | limites de versão + lock, CI (GitHub Actions), índice redundante no SQLite, cache do app sensível à data do banco | feito (CI ainda não rodou no GitHub) |
| 2 | Refatoração | módulo comum de cálculos, `app.py` dividido, mesma regra de "excluir suspeitos" no app e na planilha | pendente |
| 3 | Zeros do IRS3002 | cruzar com a planilha de Destinação Final; separar "zero confirmado" de "zero não verificado" | pendente |
| 4 | ETL e banco | execução incremental por hash, carga do staging mais limpa, destino do `.db` versionado, justificar limite de 3 kg/hab.dia | pendente |
| 5 | Entrega | README, deploy, relatório com números atualizados | pendente |
| 6 | Auditoria final | revisão independente; números do app, da planilha e do relatório batem | pendente |

Regra de ouro: os testes da etapa 0 não podem quebrar sem uma decisão explícita de mudar um número publicado.

## Orquestração: papéis, modelos e esforço

| Papel | Quem | Modelo | Esforço | Por quê |
|---|---|---|---|---|
| Orquestrador e implementador | sessão principal | Sonnet (a da sessão) | padrão | tem o contexto inteiro e conversa com o Walter; um orquestrador separado só repassaria informação |
| Leitor / explorador | subagente `Explore` ou `general-purpose` | Haiku | baixo | leitura volumosa que devolve só um resumo; erro é barato porque o orquestrador confere |
| Pesquisa de dados (planilhas SINISA) | subagente `general-purpose` | Sonnet | médio | exige raciocínio sobre estrutura, mas não decisão de projeto |
| Auditor de etapa | subagente independente, somente leitura | Opus | alto | contexto novo, sem viés de quem implementou; custa mais, mas roda uma vez por etapa |
| Auditor final (etapa 6) | subagente independente | Opus | máximo | última barreira antes de publicar números |

Regras:
1. Subagentes de implementação só rodam em paralelo se não tocam os mesmos arquivos. Caso contrário, a etapa é sequencial.
2. O auditor nunca edita: devolve achados com arquivo, linha e cenário de falha. O orquestrador corrige e pede nova checagem do que mudou.
3. Etapa só fecha quando `pytest` passa, o auditor não deixa achado aberto de severidade alta, e o resultado é commitado.
4. O esforço máximo fica restrito à auditoria final, por custo.
