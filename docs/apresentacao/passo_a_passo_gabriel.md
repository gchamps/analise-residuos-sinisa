# Preparar o notebook para a apresentação (passo a passo)

**Para:** Gabriel. **Quando:** com antecedência, hoje. **Tempo:** 20 a 30 minutos, a maior parte é download. **Precisa de:** internet.
Alguns passos abrem uma janela pedindo permissão de administrador: clique em **Sim**.

Copie cada bloco, cole no PowerShell e aperte Enter. Depois de cada passo, confira a linha **Esperado**.

> **Atalho: deixar o Claude Code fazer por você.** Abra o Claude Code em qualquer pasta e cole o texto abaixo. Ele faz os passos 1 a 9 e te avisa quando precisar de você. **Fique na frente do computador:** os passos 2 e 3 abrem a janela de administrador, e só você pode clicar em **Sim**.
>
> ```text
> Estou preparando este notebook (Windows) para uma apresentação de Administração de Banco de Dados. Use o PowerShell e me peça confirmação antes de cada instalação. Faça:
>
> 1. Se a pasta Documentos\analise-residuos-sinisa não existir, clone https://github.com/gchamps/analise-residuos-sinisa.git dentro de Documentos. Se existir, entre nela e rode git pull. Se o arquivo docs/apresentacao/passo_a_passo_gabriel.md não existir, rode git fetch e git checkout docs/apresentacao-tablespaces.
> 2. Leia docs/apresentacao/passo_a_passo_gabriel.md e execute por mim os passos 1 a 8, na ordem. Instale Git e o Visual C++ (winget) só se faltarem. Quando aparecer a janela de administrador, me avise para eu clicar em Sim.
> 3. ATENÇÃO no passo 6: NÃO rode o comando "iniciar" do postgres_portatil.ps1, porque ele trava quando a saída está sendo capturada. Em vez disso, rode ". .\docs\apresentacao\preparar_ambiente.ps1", que liga o servidor sem travar. Nesse momento ele vai mostrar [FALTA] no banco restaurado, e isso é esperado.
> 4. Depois do passo 7 (restaurar), rode ". .\docs\apresentacao\preparar_ambiente.ps1" de novo e me mostre o resultado. Preciso ver TUDO PRONTO.
> 5. Depois, rode ".\docs\apresentacao\abrir_dashboard.ps1" e espere aparecer DASHBOARD NO AR. Se faltar o Python, instale com "winget install --id Python.Python.3.12 -e" e me avise para eu abrir um PowerShell novo. A primeira vez demora alguns minutos.
> 6. Não altere nenhum arquivo do projeto e não faça commit nem push.
> ```
>
> Quando ele terminar, **confirme você mesmo** abrindo um PowerShell novo e fazendo a rotina "No dia da apresentação" (mais abaixo): precisa aparecer **TUDO PRONTO**.

---
## Passo 1: abrir o PowerShell e liberar scripts

Menu Iniciar, digite **PowerShell**, abra o **Windows PowerShell** (não precisa ser administrador). Cole:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
```

**Esperado:** nenhuma mensagem. Isso vale só para esta janela, então **repita em toda janela nova do PowerShell**. Sem isso aparece "a execução de scripts foi desabilitada neste sistema".

## Passo 2: conferir o Git

```powershell
git --version
```

**Esperado:** `git version ...`. Se aparecer erro, instale e depois **feche e abra o PowerShell**, repetindo o passo 1:

```powershell
winget install --id Git.Git -e
```

(Sem o `winget`: baixe em https://git-scm.com/download/win.)

## Passo 3: instalar o Visual C++ (o PostgreSQL precisa dele)

```powershell
winget install --id Microsoft.VCRedist.2015+.x64 -e
```

**Esperado:** "instalado com êxito" ou "já instalado". Ambos servem. Se a janela de administrador aparecer, clique em **Sim**.
(Sem o `winget`: https://aka.ms/vs/17/release/vc_redist.x64.exe)

## Passo 4: baixar o projeto

```powershell
cd $HOME\Documents
git clone https://github.com/gchamps/analise-residuos-sinisa.git
cd analise-residuos-sinisa
```

**Esperado:** a pasta `analise-residuos-sinisa` criada, com `scripts`, `sql` e `docs` dentro.
Se a pasta **já existia**, use `cd $HOME\Documents\analise-residuos-sinisa` e depois `git pull`.

## Passo 5: instalar o PostgreSQL (download de cerca de 320 MB, uma vez só)

```powershell
.\scripts\postgres_portatil.ps1 instalar
```

**Esperado:** demora alguns minutos e termina com `Instalado.` Não precisa de administrador.

## Passo 6: ligar o servidor

```powershell
.\scripts\postgres_portatil.ps1 iniciar
```

**Esperado:** `servidor iniciado`.

## Passo 7: restaurar o banco

```powershell
.\scripts\postgres_portatil.ps1 restaurar
```

**Esperado:** `Banco restaurado.` (leva uns 2 segundos).

## Passo 8: conferir tudo de uma vez

Atenção: começa com um **ponto, depois um espaço, depois outro ponto**.

```powershell
. .\docs\apresentacao\preparar_ambiente.ps1
```

**Esperado:** seis linhas `[OK]` em verde e a mensagem **TUDO PRONTO**.
Se alguma linha mostrar `[FALTA]`, leia a dica em amarelo logo abaixo dela, resolva e rode este mesmo comando de novo.

## Passo 9: abrir o dashboard (o professor também quer ver)

```powershell
.\docs\apresentacao\abrir_dashboard.ps1
```

**Esperado:** `DASHBOARD NO AR: http://localhost:8501` e o navegador abre sozinho.
- Na **primeira vez** demora de 3 a 5 minutos: cria o ambiente Python e instala as bibliotecas. Nas próximas, abre em segundos.
- A **primeira tela leva até 30 segundos** para carregar. Por isso abra o dashboard **antes** da apresentação e **deixe a aba aberta**.
- Se aparecer `[FALTA] Python 3.11 ou mais novo`: rode `winget install --id Python.Python.3.12 -e`, **feche e abra o PowerShell**, repita o passo 1 e rode este passo de novo.
- Para encerrar: feche a janelinha minimizada do Streamlit que aparece na barra de tarefas.

## Passo 10: ensaio rápido da demonstração (2 minutos, opcional, mas recomendado)

```powershell
psql -h localhost -p 5433 -U postgres -d residuos_sinisa -f docs/apresentacao/demo_postgres.sql
```

**Esperado:** aparecem blocos numerados de 1 a 9. Aperte **Enter** para passar de um bloco ao outro. No fim aparece `Fim da demonstracao`.

---

## No dia da apresentação (1 minuto)

1. Abra o PowerShell e cole o **passo 1**.
2. `cd $HOME\Documents\analise-residuos-sinisa`
3. Cole o **passo 8**. Ele **liga o servidor sozinho** se estiver desligado (acontece depois de reiniciar o notebook). Espere o **TUDO PRONTO**.
4. Deixe a janela aberta. Para aumentar a letra: **Ctrl + roda do mouse**.
5. Cole `.\docs\apresentacao\abrir_dashboard.ps1` (abre em segundos) e **espere a tela carregar**. Deixe essa aba aberta.
6. Abra também, em outra aba: https://github.com/gchamps/analise-residuos-sinisa

---

## Se der problema

| O que apareceu | O que fazer |
|---|---|
| "a execução de scripts foi desabilitada" | Cole o passo 1 de novo (janela nova perde essa liberação) |
| `git` não reconhecido | Passo 2 |
| `[FALTA] PostgreSQL executa neste computador` | Passo 3, depois o passo 5 de novo |
| `[FALTA] Servidor ligado` | Cole o passo 8 de novo; se continuar, passo 6 |
| `[FALTA] Banco restaurado` | Passo 7 |
| `psql` não reconhecido | Cole o passo 8 de novo (ele configura o caminho do `psql` nesta janela) |
| Letras quebradas na tela | Cole o passo 8 de novo na mesma janela |
| Dashboard abre em branco | Espere até 30 segundos; é normal na primeira vez |
| `[FALTA] Python 3.11 ou mais novo` | Passo 9 (instalar o Python, fechar e abrir o PowerShell) |
| Quer recomeçar o banco do zero | Passo 7 (leva 2 segundos) |

Se algum passo travar e você não entender o motivo, **cole o erro no Claude Code** e peça para ele resolver, apontando para este arquivo.

Se **nada** funcionar a tempo, tudo bem: o professor aceitou apresentar sem o banco rodando. Nesse caso, o roteiro tem um **Plano B** que usa só o navegador.
