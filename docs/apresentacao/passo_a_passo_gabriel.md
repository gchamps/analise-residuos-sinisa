# Preparar o notebook para a apresentação (passo a passo)

**Para:** Gabriel. **Quando:** com antecedência, hoje. **Tempo:** 15 a 25 minutos, a maior parte é download. **Precisa de:** internet.
Alguns passos abrem uma janela pedindo permissão de administrador: clique em **Sim**.

Copie cada bloco, cole no PowerShell e aperte Enter. Depois de cada passo, confira a linha **Esperado**.

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

## Passo 9: ensaio rápido (2 minutos, opcional, mas recomendado)

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
5. Abra também, no navegador: https://github.com/gchamps/analise-residuos-sinisa

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
| Quer recomeçar o banco do zero | Passo 7 (leva 2 segundos) |

Se **nada** funcionar a tempo, tudo bem: o professor aceitou apresentar sem o banco rodando. Nesse caso, o roteiro tem um **Plano B** que usa só o navegador.
