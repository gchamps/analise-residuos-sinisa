# Sobe o dashboard (Streamlit) e abre no navegador.
#
# Uso, na raiz do projeto, no PowerShell:
#     .\docs\apresentacao\abrir_dashboard.ps1
#
# O que faz:
#   1. procura o Python (3.11 ou mais novo);
#   2. cria o ambiente .venv e instala as dependencias, se ainda nao existirem (so na 1a vez);
#   3. sobe o dashboard na porta 8501 e abre http://localhost:8501 no navegador.
# O dashboard le dados_tratados\projeto_residuos.db, que ja vem no repositorio (nao precisa de ETL nem de PostgreSQL).
# Para encerrar: feche a janela minimizada do Streamlit que apareceu na barra de tarefas.

$porta = 8501
$url = "http://localhost:$porta"
$raiz = (Get-Location).Path

function Resultado($ok, $mensagem, $dica) {
    if ($ok) { Write-Host "  [OK]    $mensagem" -ForegroundColor Green }
    else { Write-Host "  [FALTA] $mensagem" -ForegroundColor Red; if ($dica) { Write-Host "          -> $dica" -ForegroundColor Yellow } }
}

function DashboardNoAr { try { return ((Invoke-WebRequest "$url/_stcore/health" -UseBasicParsing -TimeoutSec 2).Content -eq "ok") } catch { return $false } }

Write-Host ""
Write-Host "Preparando o dashboard..."

if (-not (Test-Path ".\scripts\app.py")) {
    Resultado $false "Nao achei scripts\app.py" "voce esta na raiz do projeto? use: cd `$HOME\Documents\analise-residuos-sinisa"
    return
}

# ja esta no ar? so abre o navegador
if (DashboardNoAr) {
    Resultado $true "Dashboard ja estava no ar" $null
    Start-Process $url
    Write-Host ""; Write-Host "DASHBOARD NO AR: $url" -ForegroundColor Green; Write-Host ""
    return
}

# 1) Python 3.11+ (ignora o atalho da Microsoft Store, que nao e um Python de verdade)
function PythonValido($exe) {
    try {
        $saida = (& $exe --version 2>&1 | Out-String).Trim()
        if ($saida -match "^Python 3\.(\d+)") { return ([int]$Matches[1] -ge 11) }
    } catch { }
    return $false
}
$python = $null
$candidatos = @("python", (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"), (Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\python.exe"), (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"))
foreach ($c in $candidatos) { if (PythonValido $c) { $python = $c; break } }
Resultado ($null -ne $python) "Python 3.11 ou mais novo encontrado" "instale: winget install --id Python.Python.3.12 -e   (depois FECHE e abra o PowerShell, repita o passo 1 do guia e rode este script de novo)"
if (-not $python) { return }

# 2) ambiente virtual e dependencias
$venvPython = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "  ...     criando o ambiente Python (.venv)..." -ForegroundColor Yellow
    & $python -m venv .venv
}
Resultado (Test-Path $venvPython) "Ambiente .venv" "apague a pasta .venv e rode este script de novo"
if (-not (Test-Path $venvPython)) { return }

& $venvPython -c "import streamlit, pandas, altair, scipy" > $null 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ...     instalando as dependencias (1 a 3 minutos, so na primeira vez)..." -ForegroundColor Yellow
    & $venvPython -m pip install --quiet --disable-pip-version-check -r requirements.lock.txt
    & $venvPython -c "import streamlit, pandas, altair, scipy" > $null 2>&1
}
Resultado ($LASTEXITCODE -eq 0) "Dependencias instaladas" "confira a internet e rode este script de novo"
if ($LASTEXITCODE -ne 0) { return }

# 3) sobe o dashboard (janela minimizada) e espera ficar no ar
Write-Host "  ...     subindo o dashboard..." -ForegroundColor Yellow
Start-Process -FilePath $venvPython -WindowStyle Minimized -WorkingDirectory $raiz `
    -ArgumentList "-m streamlit run scripts/app.py --server.headless true --server.port $porta --browser.gatherUsageStats false"
$noAr = $false
for ($i = 0; $i -lt 45 -and -not $noAr; $i++) { Start-Sleep -Seconds 1; $noAr = DashboardNoAr }
Resultado $noAr "Dashboard respondendo na porta $porta" "olhe a janela minimizada do Streamlit para ver o erro"

Write-Host ""
if ($noAr) {
    Start-Process $url
    Write-Host "DASHBOARD NO AR: $url" -ForegroundColor Green
    Write-Host "(a 1a tela demora uns segundos para carregar; para encerrar, feche a janela minimizada do Streamlit)"
}
Write-Host ""
