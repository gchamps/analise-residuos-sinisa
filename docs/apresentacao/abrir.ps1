# Abre, com um comando, cada coisa que sera mostrada na apresentacao.
#
# Uso, na raiz do projeto, no PowerShell:
#     .\docs\apresentacao\abrir.ps1        (sem numero: mostra a lista)
#     .\docs\apresentacao\abrir.ps1 2      (abre o item 2)
#
# Os numeros sao os MESMOS passos do roteiro_pratico.md.
# Os itens do GitHub abrem no navegador padrao. Itens "arquivo" abrem no Excel.
# Teste sem abrir nada:  .\docs\apresentacao\abrir.ps1 2 -SoMostrar

param([string]$Item = "", [switch]$SoMostrar)

$raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$repo = "https://github.com/gchamps/analise-residuos-sinisa"
$blob = "$repo/blob/main"

$itens = [ordered]@{
    "1"  = @{ passo = "1";  nome = "Repositorio no GitHub";                                   tipo = "url";       alvo = $repo }
    "2"  = @{ passo = "2";  nome = "Documentacao do banco: diagrama do pipeline e do modelo"; tipo = "url";       alvo = "$blob/docs/banco_de_dados.md" }
    "3"  = @{ passo = "3";  nome = "Planilha original do SINISA (so olhar o cabecalho)";      tipo = "arquivo";   alvo = "dados_originais\SINISA_RESIDUOS_Indicadores_2024.xlsx" }
    "4"  = @{ passo = "4";  nome = "Script do esquema (01_schema.sql)";                       tipo = "url";       alvo = "$blob/sql/postgres/01_schema.sql" }
    "6"  = @{ passo = "6";  nome = "Script do tratamento em SQL (02_transformacao.sql)";      tipo = "url";       alvo = "$blob/sql/postgres/02_transformacao.sql" }
    "8"  = @{ passo = "8";  nome = "Views e consultas de exemplo (03_views_e_consultas.sql)"; tipo = "url";       alvo = "$blob/sql/postgres/03_views_e_consultas.sql" }
    "11" = @{ passo = "11"; nome = "Planilha de analise estatistica (Excel)";                 tipo = "arquivo";   alvo = "resultados\Analise_Estatistica_Residuos.xlsx" }
    "12" = @{ passo = "12"; nome = "Dashboard (precisa estar no ar)";                         tipo = "dashboard"; alvo = "http://localhost:8501" }
    "13" = @{ passo = "8";  nome = "As 11 consultas estatisticas (02_consultas.sql)";         tipo = "url";       alvo = "$blob/sql/02_consultas.sql" }
}

function MostrarLista {
    Write-Host ""
    Write-Host "Itens da apresentacao (use: .\docs\apresentacao\abrir.ps1 N):"
    foreach ($k in $itens.Keys) {
        $i = $itens[$k]
        Write-Host ("  {0,3}  {1}" -f $k, $i.nome) -NoNewline
        if ($k -eq "13") { Write-Host "  (extra do passo 8)" -ForegroundColor DarkGray } else { Write-Host "" }
    }
    Write-Host ""
    Write-Host "Os passos 5, 7, 9 e 10 sao no psql (demo_postgres.sql); o passo 11 tambem mostra o backup."
    Write-Host ""
}

if ($Item -eq "" -or -not $itens.Contains($Item)) {
    if ($Item -ne "") { Write-Host "Item '$Item' nao existe." -ForegroundColor Red }
    MostrarLista
    return
}

$i = $itens[$Item]
$alvo = $i.alvo
if ($i.tipo -eq "arquivo") { $alvo = Join-Path $raiz $i.alvo }

Write-Host ""
Write-Host "Abrindo [$Item]: $($i.nome)" -ForegroundColor Cyan
Write-Host "  $alvo"

if ($SoMostrar) { Write-Host ""; return }

if ($i.tipo -eq "arquivo" -and -not (Test-Path $alvo)) {
    Write-Host "  [FALTA] arquivo nao encontrado. Voce esta na raiz do projeto? Rode: git pull" -ForegroundColor Red
    return
}
if ($i.tipo -eq "dashboard") {
    $noAr = $false
    try { $noAr = ((Invoke-WebRequest "$alvo/_stcore/health" -UseBasicParsing -TimeoutSec 2).Content -eq "ok") } catch { }
    if (-not $noAr) {
        Write-Host "  [FALTA] o dashboard nao esta no ar. Rode primeiro: .\docs\apresentacao\abrir_dashboard.ps1" -ForegroundColor Red
        return
    }
}
try { Start-Process $alvo } catch {
    Write-Host "  [FALTA] nao consegui abrir. Abra manualmente: $alvo" -ForegroundColor Red
}
Write-Host ""
