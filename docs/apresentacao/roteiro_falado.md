# Roteiro falado (para ler na apresentação)

Disciplina: **Administração de Banco de Dados**. Duração: cerca de 13 minutos falando, mais as pausas da demonstração.
Linhas entre colchetes, como **[DEMO 4]**, indicam o passo do `roteiro_pratico.md`. Não leia os colchetes em voz alta.
Dica: fale devagar, com frases curtas, e olhe para o professor entre uma frase e outra.

---

## 1. Abertura (cerca de 1 minuto)

"Bom dia, professor. Eu vou apresentar o que o nosso grupo fez no projeto de extensão, focando na parte de **banco de dados**.

O projeto analisa **dados abertos do governo sobre resíduos sólidos**, da base **SINISA**, que é o Sistema Nacional de Informações em Saneamento Básico. São dados de **5.570 municípios** do Brasil.

O objetivo é transformar uma planilha grande e bagunçada em um **banco organizado**, que alimenta as análises estatísticas, o dashboard e a planilha do projeto.

Vou mostrar o caminho completo: de onde o dado veio, como foi tratado, como foi guardado e como ele é usado. E vou ligar cada passo ao que vimos em aula."

**[DEMO 1: abrir o repositório no GitHub]**

"Tudo está no GitHub: os dados brutos, os scripts, os arquivos SQL e a documentação."

---

## 2. Extração dos dados (cerca de 2 minutos)

**[DEMO 2: abrir `docs/banco_de_dados.md` e o diagrama do pipeline]**

"Este é o fluxo do nosso banco. Ele segue a ideia de **ELT**: primeiro **extrair e carregar** o dado bruto, e só depois **transformar dentro do banco**.

O primeiro passo é a **extração**."

**[DEMO 3: abrir a planilha do SINISA]**

"A fonte é uma planilha em Excel do Ministério das Cidades. Ela tem um problema: o **cabeçalho é dividido em duas linhas**. O código do indicador fica numa linha e a unidade em outra. E os municípios que não responderam vêm com campos vazios.

Por isso fizemos um script em **Python**, com a biblioteca **pandas**, que lê a planilha e monta o cabeçalho certo.

Depois, em vez de limpar tudo em Python, nós gravamos a planilha **do jeito que veio**, toda como texto, numa área chamada **staging**. Fazemos isso com o comando `COPY` do PostgreSQL, que é o jeito mais rápido de carregar muitos dados.

Guardar o dado bruto tem uma vantagem: dá para **auditar a carga**. Cada linha do staging guarda a posição da linha de origem."

---

## 3. A estrutura do banco (cerca de 3 minutos)

**[DEMO 4: rodar o script, blocos 1 e 2]**

"Agora a estrutura. Usamos o **PostgreSQL** e organizamos o banco em dois **schemas**: o `staging`, que é o bruto, e o `sinisa`, que é o modelo final.

No schema `sinisa` usamos o **esquema estrela**, um modelo dimensional, que é o mais usado para análise.

Temos duas **dimensões**: a tabela `municipio`, com código IBGE, nome, UF, região e população; e a tabela `indicador`, com o catálogo dos seis indicadores que usamos.

E temos a **tabela fato**, `resultado_indicador`: uma linha para cada município, em cada indicador. Se amanhã entrar um indicador novo, não precisa mudar a estrutura da tabela.

Uma decisão consciente: a coluna `região` fica dentro de `municipio`, mesmo dependendo da UF. Em um esquema estrela as dimensões são **desnormalizadas de propósito**, para as consultas ficarem mais simples.

Olhando a tabela fato, aparecem os conceitos da disciplina. Os **tipos de dados**: o código IBGE é `CHAR(7)`, porque tem sempre sete dígitos. A **chave primária** é um identificador gerado automaticamente. As **chaves estrangeiras** ligam a fato aos municípios e aos indicadores. A restrição `UNIQUE` impede o mesmo resultado repetido. E as restrições `CHECK` garantem que o valor não seja negativo.

Também criamos **índices**, por exemplo, por indicador, para acelerar as consultas. E documentamos tudo com `COMMENT`."

---

## 4. Tratamento e armazenamento (cerca de 2 minutos)

**[DEMO 5: blocos 3 e 4]**

"Aqui está o tratamento. Do lado do staging estão as linhas como vieram: os municípios que não responderam estão com campos vazios.

O tratamento é feito por um script SQL, `02_transformacao.sql`, **dentro do banco**."

**[DEMO 6: mostrar os comentários do topo do arquivo]**

"As regras são: tirar espaços e a parte decimal do código IBGE; transformar 'Sim' e 'Não' em verdadeiro e falso; guardar só valores numéricos; e **marcar**, sem apagar, valores suspeitos, como porcentagem acima de 100.

Outro ponto: a planilha é **larga**, com uma linha por município. O SQL transforma isso na tabela fato **longa**. São 5.570 municípios; 4.854 responderam; e 4.854 vezes 6 indicadores dá **29.124 linhas**, exatamente o que está na fato.

Esse processo roda dentro de **uma única transação**. Se qualquer passo falhar, o banco desfaz tudo e não fica pela metade. Depois da carga, rodamos o `ANALYZE`, que atualiza as estatísticas para o otimizador.

E validamos: o script de validação confere se todos os respondentes têm resultado, se não sobrou nada de quem não respondeu e se as contagens batem. O resultado é zero problemas."

**[DEMO 7: bloco 5]**

"A integridade também é do banco. Se eu tentar inserir um valor negativo, ele recusa por causa do `CHECK`. Se eu usar um município que não existe, recusa pela chave estrangeira. E se eu repetir um resultado, recusa pela `UNIQUE`. Estou usando `BEGIN` e `ROLLBACK`, então nada é alterado."

---

## 5. Uso dos dados na análise estatística (cerca de 2 minutos)

**[DEMO 8: blocos 6 e 7]**

"Agora, como o banco é usado na análise. Criamos **views**: a primeira junta as três tabelas e coloca os seis indicadores em colunas, um município por linha. As outras calculam, por UF e por região, a **média simples**, a **média ponderada pela população** e a **mediana**.

A mediana usa uma função própria do PostgreSQL, a `percentile_cont`. E o ranking usa uma **função de janela**, o `rank() over`.

Por que média simples e ponderada? Porque um município pequeno pesa o mesmo que uma capital na média simples. A ponderada corrige isso usando a população.

Também olhamos o **plano de execução** com `EXPLAIN ANALYZE`. A consulta por indicador usa o **índice** que criamos, e executa em poucos milissegundos.

No projeto, essa análise vira três produtos: um conjunto de **onze consultas SQL** estatísticas, uma **planilha Excel** com médias, ranking e probabilidades, e um **dashboard** em Python."

Se sobrar tempo, mostrar a planilha: "Esta é a planilha, feita a partir dos mesmos dados do banco."

*(Uma observação honesta, se perguntarem:)* "O dashboard lê uma **cópia do banco em SQLite**, porque o serviço onde ele será publicado não alcança um PostgreSQL local. As duas cargas partem da mesma planilha e foram conferidas: as contagens e as somas são iguais."

---

## 6. Administração: segurança e backup (cerca de 1 minuto)

**[DEMO 9: bloco 8]**

"Na parte de administração, criamos um **usuário só de leitura**, o `leitor_sinisa`, com `GRANT SELECT`. Quem só consulta, como o dashboard, não precisa alterar dados. Vejam: ele consegue ler, mas ao tentar apagar, o banco **nega a permissão**."

**[DEMO 10: backup]**

"Para **backup**, usamos o `pg_dump`. E temos um script que **restaura** o banco inteiro a partir desse dump em poucos segundos. É assim que se reconstrói o banco do zero."

---

## 7. Fechamento (cerca de 1 minuto)

"Para fechar, resumindo o que aplicamos da matéria: **modelagem dimensional**, **tipos de dados** e **restrições de integridade**, **schemas**, **ETL com carga em lote**, **transações**, **índices e plano de execução**, **views**, **consultas com função de janela**, **usuários e privilégios**, e **backup e restauração**.

Como limitação: o servidor local está configurado só para estudo, sem senha e aceitando apenas conexões da própria máquina. Em produção usaríamos autenticação e permissões mais restritas.

Obrigado. Fico à disposição para perguntas."

---

# Perguntas que o professor pode fazer (respostas curtas)

**Por que esquema estrela e não só tabelas normalizadas?**
"Porque o foco é análise: poucas junções, consultas simples e rápidas. A fato guarda os valores e as dimensões descrevem município e indicador."

**Por que usar staging?**
"Para guardar o dado exatamente como veio, auditar a carga e fazer a limpeza em SQL, sem mexer na origem."

**E se o processo de carga falhar no meio?**
"Esquema, carga e transformação rodam em uma transação só. Se falhar, o PostgreSQL desfaz tudo."

**Por que marcar valores suspeitos em vez de apagar?**
"Para não perder informação. Quem analisa decide se exclui ou não. No dashboard há uma opção para isso."

**Por que índice numa coluna com só seis valores diferentes?**
"Resposta honesta: o ganho é pequeno, porque cada indicador tem cerca de um sexto das linhas. O plano usa um Bitmap Index Scan. É útil para filtrar um indicador e custa pouco, porque a tabela é pequena."

**Por que `DOUBLE PRECISION` e não `NUMERIC`?**
"Os indicadores são taxas medidas, não valores financeiros. A precisão exata do `NUMERIC` não era necessária."

**Por que os números do identificador pulam (por exemplo, 29.125)?**
"Porque a sequência do `IDENTITY` não volta atrás no `ROLLBACK`. Nos testes de erro, o número foi consumido mesmo sem inserir a linha. É o comportamento esperado do PostgreSQL."

**Por que `CHAR(7)` para o código IBGE?**
"Porque o código tem sempre sete dígitos, e assim a restrição `CHECK` valida o formato."

**Como vocês garantiram que SQLite e PostgreSQL têm os mesmos dados?**
"O ETL compara contagens e somas por indicador entre os dois bancos. Todas batem."

**Qual a diferença entre média simples e ponderada?**
"A simples dá o mesmo peso a cada município; a ponderada usa a população como peso. Na disposição inadequada do Brasil, a simples dá cerca de 34% e a ponderada cerca de 21%."

**O que é ELT, e por que não ETL?**
"No ETL a transformação acontece antes do banco, em outra ferramenta. No ELT carregamos o bruto e transformamos dentro do banco, com SQL. Escolhemos ELT porque o PostgreSQL faz essa limpeza bem e fica documentada em SQL."

**O que não está no PostgreSQL?**
"Duas tabelas de apoio que criamos depois, uma de destinação dos resíduos e outra de controle do ETL, existem só no SQLite. A camada PostgreSQL tem o modelo principal, as views e o usuário de leitura."
