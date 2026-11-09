# Plano de melhorias

Registro do plano de trabalho, do modelo de orquestração e do andamento. Atualizado a cada etapa.

## Etapas

| # | Etapa | Entregas | Status |
|---|---|---|---|
| 0 | Auditoria de base | `tests/` de caracterização (números hoje publicados) e do ETL, `requirements-dev.txt`; auditada, achados médios corrigidos | feito |
| 1 | Fundação | limites de versão + lock, CI (GitHub Actions), índice redundante no SQLite, cache do app sensível à data do banco | feito (CI ainda não rodou no GitHub) |
| 2 | Refatoração | `scripts/calculos.py` (cálculos comuns a app, análise e planilha), `scripts/mapa.py`, `app.py` enxuto, `carregar_dados(excluir_sinalizados)` na análise, testes do módulo e do app inteiro (Streamlit AppTest) | feito, aguardando auditoria |
| 3 | Zeros do IRS3002 | tabela `destinacao_municipio` com a massa das rotas de coleta por classe de destino (2ª aba da planilha de Manejo, GTR1008/GTR1011) e as massas coletada/recuperada; o ETL **confere o IRS3002 contra as rotas nos 4.854 municípios** (maior diferença 0,005 p.p.) e falha se divergir; `classificar_zeros` em `calculos.py`; quadro "O que significa um 0%?" no app. Resultado: de 3.057 zeros, 2.880 (94%) com rotas a aterro sanitário/inertes cobrindo ≥90% da massa líquida, 174 com destino final não informado (transbordo, triagem, compostagem), 3 incompletos, 0 contraditórios. Nenhuma UF passa de 12% de zeros sem rota a aterro | feito; **refeito duas vezes** após achados altos da auditoria (ver abaixo); nova auditoria pendente |
| 4 | ETL e banco | execução incremental por hash, carga do staging mais limpa, destino do `.db` versionado, justificar limite de 3 kg/hab.dia | pendente |
| 5 | Entrega | README, deploy, relatório com números atualizados | pendente |
| 6 | Auditoria final | revisão independente; números do app, da planilha e do relatório batem | pendente |

### Lições da etapa 3
1. 1ª versão: usei as unidades de disposição sediadas em cada município (1ª aba da planilha de Destinação Final) e concluí que 78% dos zeros eram "não verificáveis". O auditor mostrou que a 2ª aba traz os fluxos origem → destino.
2. 2ª versão: usei esses fluxos (declarados pelo município **receptor**) e achei que o indicador saía deles. A reauditoria mostrou que o IRS3002 sai das **rotas de coleta declaradas pelo município de origem** (2ª aba da planilha de Manejo), o que o próprio ETL agora comprova numericamente. As "UFs de atenção" (RN, GO, SE) eram artefato da fonte errada.
3. Prática adotada: antes de interpretar um indicador, reproduzi-lo a partir da fonte candidata. Se não reproduz, a fonte está errada. Esse teste agora roda no ETL e nos testes.

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
