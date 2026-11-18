# Prepara e confere o ambiente da demonstracao (PostgreSQL portatil + banco restaurado).
#
# Uso, na raiz do projeto, no PowerShell (note o PONTO e o ESPACO no inicio):
#     . .\docs\apresentacao\preparar_ambiente.ps1
#
# O que faz:
#   1. configura o terminal (acentos e caminho do psql) NESTA janela;
#   2. confere se o PostgreSQL esta instalado e funcionando;
#   3. liga o servidor se estiver desligado;
#   4. confere se o banco foi restaurado (5570 municipios).
# No fim mostra "TUDO PRONTO" ou diz o que falta.

chcp 65001 > $null
$env:PGCLIENTENCODING = "UTF8"       # os DADOS (Sao Paulo, Nao...) saem com acento correto
$env:LANGUAGE = "en"                 # rotulos do psql em ingles: em portugues eles saem com caracteres quebrados no Windows
$pgRaiz = Join-Path $env:USERPROFILE "tools\pg"
$pgBin = Join-Path $pgRaiz "pgsql\bin"
$pgDados = Join-Path $pgRaiz "data"
$env:Path = "$pgBin;" + $env:Path
$pronto = $true

function Resultado($ok, $mensagem, $dica) {
    if ($ok) { Write-Host "  [OK]    $mensagem" -ForegroundColor Green }
    else { Write-Host "  [FALTA] $mensagem" -ForegroundColor Red; if ($dica) { Write-Host "          -> $dica" -ForegroundColor Yellow }; $script:pronto = $false }
}

Write-Host ""
Write-Host "Conferindo o ambiente da demonstracao..."

# 1) o PostgreSQL esta instalado e executa? (falha com codigo -1073741515 se faltar o Visual C++)
$instalado = Test-Path (Join-Path $pgBin "postgres.exe")
Resultado $instalado "PostgreSQL portatil instalado" "rode: .\scripts\postgres_portatil.ps1 instalar"
$executa = $false
if ($instalado) {
    & (Join-Path $pgBin "postgres.exe") --version > $null 2>&1
    $executa = ($LASTEXITCODE -eq 0)
}
if ($instalado) {
    Resultado $executa "PostgreSQL executa neste computador" "instale o Visual C++: winget install --id Microsoft.VCRedist.2015+.x64 -e (aceite a janela de administrador) e rode o 'instalar' de novo"
}

# 2) pasta de dados criada?
$temDados = Test-Path (Join-Path $pgDados "PG_VERSION")
Resultado $temDados "Pasta de dados criada" "rode de novo: .\scripts\postgres_portatil.ps1 instalar"

# 3) servidor ligado? (liga sozinho se estiver desligado)
function ServidorLigado { return [bool](Test-NetConnection localhost -Port 5433 -WarningAction SilentlyContinue -InformationLevel Quiet) }
$ligado = $false
if ($instalado -and $executa -and $temDados) {
    $ligado = ServidorLigado
    if (-not $ligado) {
        Write-Host "  ...     servidor desligado, ligando..." -ForegroundColor Yellow
        Start-Process -FilePath (Join-Path $pgBin "pg_ctl.exe") -WindowStyle Hidden `
            -ArgumentList "-D `"$pgDados`" -o `"-p 5433 -c listen_addresses=localhost`" -l `"$(Join-Path $pgRaiz 'server.log')`" start"
        for ($i = 0; $i -lt 20 -and -not $ligado; $i++) { Start-Sleep -Seconds 1; $ligado = ServidorLigado }
    }
}
Resultado $ligado "Servidor ligado na porta 5433" "rode: .\scripts\postgres_portatil.ps1 iniciar"

# 4) banco restaurado?
$municipios = ""
if ($ligado) { $municipios = (& psql -h localhost -p 5433 -U postgres -d residuos_sinisa -t -A -c "SELECT count(*) FROM sinisa.municipio;" 2>$null) }
Resultado ("$municipios".Trim() -eq "5570") "Banco restaurado (5570 municipios)" "rode: .\scripts\postgres_portatil.ps1 restaurar"

# 5) script da demonstracao presente?
Resultado (Test-Path ".\docs\apresentacao\demo_postgres.sql") "Script da demonstracao encontrado" "voce esta na raiz do projeto? rode: git pull"

Write-Host ""
if ($pronto) {
    Write-Host "TUDO PRONTO. Para apresentar:" -ForegroundColor Green
    Write-Host '  psql -h localhost -p 5433 -U postgres -d residuos_sinisa -f docs/apresentacao/demo_postgres.sql'
} else {
    Write-Host "FALTA ALGO: siga a dica em amarelo acima e rode este comando de novo." -ForegroundColor Red
}
Write-Host ""
