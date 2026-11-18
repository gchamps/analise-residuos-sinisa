# Roteiro falado (para ler na apresentação)

Disciplina: **Administração de Banco de Dados**. Duração: cerca de 15 minutos falando, mais as pausas da demonstração.
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

## 6. Administração: segurança, armazenamento e backup (cerca de 2 minutos)

**[DEMO 9: bloco 8]**

"Na parte de administração, criamos um **usuário só de leitura**, o `leitor_sinisa`, com `GRANT SELECT`. Quem só consulta, como o dashboard, não precisa alterar dados. Vejam: ele consegue ler, mas ao tentar apagar, o banco **nega a permissão**."

**[DEMO 10: bloco 9]**

"Sobre o **armazenamento físico**. No PostgreSQL, os dados ficam em arquivos dentro de uma **pasta de dados**. Cada tabela é um arquivo, gravado em **páginas de 8 quilobytes**. E um **tablespace** é o que liga tabelas e índices a um local do disco.

Neste projeto, **nós não criamos um tablespace próprio**. O banco é pequeno, uns 13 megabytes, e fica todo no tablespace padrão, o `pg_default`. O comando `\db` mostra só os dois que o PostgreSQL já traz, e a consulta mostra que todas as nossas tabelas e índices estão no `pg_default`.

Em um banco grande, a ideia seria **separar por disco**: as tabelas maiores em um disco, os índices em um disco mais rápido, ou dados antigos em um disco mais barato. Para isso, cria-se o tablespace apontando para uma pasta vazia e move-se o objeto, com `CREATE TABLESPACE` e `ALTER INDEX ... SET TABLESPACE`. Esse exemplo está no fim do script, só como comentário, sem executar."

**[DEMO 11: backup]**

"Para **backup**, usamos o `pg_dump`. E temos um script que **restaura** o banco inteiro a partir desse dump em poucos segundos. É assim que se reconstrói o banco do zero."

---

## 7. Dashboard (cerca de 1 minuto)

**[DEMO 12: navegador em localhost:8501, já aberto]**

"Para terminar a parte prática, o resultado que chega ao usuário: este é o **dashboard** que lê esses dados. Foi feito em **Python, com Streamlit**, e consome uma **cópia do banco em SQLite**, porque o serviço de hospedagem não alcança um PostgreSQL local.

Na primeira tela estão os principais números, como a média nacional de disposição inadequada e a cobertura da coleta. O mapa mostra a disposição inadequada por estado. Na aba Estados está o ranking com a média simples e a ponderada, que são as mesmas estatísticas das views que mostrei no banco. E na aba Método estão as definições dos indicadores, que vêm da tabela `indicador`."

---

## 8. Fechamento (cerca de 1 minuto)

"Para fechar, resumindo o que aplicamos da matéria: **modelagem dimensional**, **tipos de dados** e **restrições de integridade**, **schemas**, **ETL com carga em lote**, **transações**, **índices e plano de execução**, **views**, **consultas com função de janela**, **usuários e privilégios**, e **backup e restauração**.

Como limitação: o servidor local está configurado só para estudo, sem senha e aceitando apenas conexões da própria máquina. Em produção usaríamos autenticação e permissões mais restritas. Também não aplicamos particionamento, tablespaces separados nem backup físico, porque o volume de dados é pequeno.

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

**Vocês usaram tablespace?**
"Não criamos um próprio. O banco é pequeno e fica todo no padrão, o `pg_default`. Mostrei isso na consulta. Em um banco grande, usaríamos tablespaces para separar tabelas e índices em discos diferentes, por desempenho ou custo."

**Por que não usaram?**
"Porque o ganho aparece com volume e com discos diferentes. Aqui são 13 megabytes em uma máquina só. Criar tablespace só para mostrar seria complicar sem benefício."

**O que é um tablespace, em uma frase?**
"É um local no disco onde o PostgreSQL guarda os arquivos de tabelas e índices, escolhido pelo administrador."

**Onde ficam fisicamente os dados?**
"Em uma pasta de dados, o `data_directory`. Cada tabela e índice é um arquivo, em páginas de 8 quilobytes. A consulta do bloco 9 mostra o caminho do arquivo da tabela fato."

**O que garante que um dado confirmado não se perde se o computador cair?**
"O log de transações, o WAL: o PostgreSQL grava a mudança no log antes de gravar nos arquivos de dados. É padrão e não precisamos configurar. Aparece no log do servidor como os *checkpoints*."

**E o VACUUM?**
"O PostgreSQL mantém versões das linhas (MVCC) e o autovacuum limpa as antigas, ligado por padrão. O que nós rodamos, na carga, foi o `ANALYZE`, para atualizar as estatísticas do otimizador."

**Qual o nível de isolamento das transações?**
"Usamos o padrão do PostgreSQL, o `READ COMMITTED`. Não configuramos outro, porque a carga roda sozinha e não há concorrência."

**Que tipo de backup vocês fizeram?**
"Backup **lógico**, com o `pg_dump`, que gera os comandos SQL para recriar o banco. Não fizemos backup **físico**, com cópia dos arquivos e arquivamento do WAL, que permite recuperar até um instante no tempo. Para este tamanho, o lógico basta."

**Como é feita a autenticação?**
"O servidor local usa o método `trust` no arquivo `pg_hba.conf`, aceitando só conexões da própria máquina, sem senha. É de estudo. Em produção, usaríamos senha ou certificado e restringiríamos por usuário."

---

# Conceitos de administração: o que aplicamos, o que só explicamos e o que não aplicamos

Use esta tabela para não dizer que fez algo que não fez. Se o professor perguntar, responda pela coluna certa.

| Conceito | Situação | Como falar |
|---|---|---|
| Modelagem dimensional, tipos, `PK`, `FK`, `UNIQUE`, `CHECK`, `NOT NULL` | **Aplicamos** | "Está no esquema; mostrei na tabela fato." |
| Schemas | **Aplicamos** | "`staging` e `sinisa`." |
| Índices e `EXPLAIN ANALYZE` | **Aplicamos** | "Três índices; o plano usa o do indicador." |
| Views e funções de janela | **Aplicamos** | "Três views e `rank() OVER`." |
| Transações | **Aplicamos** | "Carga numa transação; `BEGIN`/`ROLLBACK` nos testes." |
| Usuários e privilégios | **Aplicamos** | "Papel `leitor_sinisa` com `GRANT SELECT`." |
| Backup lógico (`pg_dump`) e restauração | **Aplicamos** | "Dump versionado e script que restaura." |
| `ANALYZE` e estatísticas | **Aplicamos** | "Rodado ao final da carga." |
| Tablespaces | **Só explicamos** | "Tudo no `pg_default`; mostrei onde ficam os arquivos." |
| Páginas de 8 KB, WAL, MVCC, autovacuum, isolamento | **Padrão do PostgreSQL, só explicamos** | "Funcionam por padrão; não configuramos." |
| `pg_hba.conf` (autenticação) | **Só explicamos** | "`trust` só em localhost, por ser banco de estudo." |
| Particionamento, replicação, alta disponibilidade | **Não aplicamos** | "Volume pequeno; seria evolução futura." |
| Backup físico e recuperação em ponto no tempo | **Não aplicamos** | "Para este tamanho, o backup lógico basta." |