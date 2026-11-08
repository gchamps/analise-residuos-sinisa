<#
  Postgres portátil para o projeto (Windows, sem instalador e sem administrador).

  Uso, a partir da raiz do projeto (PowerShell):
      .\scripts\postgres_portatil.ps1 instalar     # baixa e descompacta (uma vez, ~320 MB) e cria a pasta de dados
      .\scripts\postgres_portatil.ps1 iniciar      # liga o servidor em localhost:5433
      .\scripts\postgres_portatil.ps1 status       # mostra se está rodando
      .\scripts\postgres_portatil.ps1 parar        # desliga o servidor
      .\scripts\postgres_portatil.ps1 restaurar    # recria o banco a partir de dados_tratados/postgres/residuos_sinisa.sql
      .\scripts\postgres_portatil.ps1 psql         # abre o console SQL no banco do projeto

  Tudo fica em %USERPROFILE%\tools\pg (apague a pasta para remover).
  O servidor aceita conexões só deste computador (localhost) e usa autenticação "trust",
  adequada para um banco local de estudo. Não use esta configuração em produção.
#>
param([Parameter(Mandatory = $true)][ValidateSet('instalar', 'iniciar', 'parar', 'status', 'restaurar', 'psql')][string]$acao)

$versao = '18.1-1'
$porta = 5433
$raiz = Join-Path $env:USERPROFILE 'tools\pg'
$bin = Join-Path $raiz 'pgsql\bin'
$dados = Join-Path $raiz 'data'
$log = Join-Path $raiz 'server.log'
$dump = Join-Path (Split-Path $PSScriptRoot -Parent) 'dados_tratados\postgres\residuos_sinisa.sql'

switch ($acao) {
    'instalar' {
        if (-not (Test-Path (Join-Path $bin 'postgres.exe'))) {
            New-Item -ItemType Directory -Force $raiz | Out-Null
            $zip = Join-Path $raiz 'pg.zip'
            $url = "https://get.enterprisedb.com/postgresql/postgresql-$versao-windows-x64-binaries.zip"
            Write-Host "Baixando $url ..."
            $ProgressPreference = 'SilentlyContinue'
            Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
            Expand-Archive $zip -DestinationPath $raiz -Force
            Remove-Item $zip
        }
        if (-not (Test-Path $dados)) {
            & (Join-Path $bin 'initdb.exe') -D $dados -U postgres -A trust -E UTF8 --locale=C
        }
        Write-Host 'Instalado. Próximo passo: iniciar.'
    }
    'iniciar' {
        & (Join-Path $bin 'pg_ctl.exe') -D $dados -o "-p $porta -c listen_addresses=localhost" -l $log start
    }
    'parar' { & (Join-Path $bin 'pg_ctl.exe') -D $dados stop }
    'status' { & (Join-Path $bin 'pg_ctl.exe') -D $dados status }
    'restaurar' {
        if (-not (Test-Path $dump)) { throw "Dump não encontrado: $dump" }
        $psql = Join-Path $bin 'psql.exe'
        & $psql -h localhost -p $porta -U postgres -d postgres -c 'DROP DATABASE IF EXISTS residuos_sinisa;'
        # O dump concede SELECT ao papel de leitura; papéis são do servidor, então ele precisa existir antes.
        & $psql -h localhost -p $porta -U postgres -d postgres -c "DO `$`$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'leitor_sinisa') THEN CREATE ROLE leitor_sinisa LOGIN; END IF; END `$`$;"
        & $psql -h localhost -p $porta -U postgres -d postgres -c "CREATE DATABASE residuos_sinisa ENCODING 'UTF8' TEMPLATE template0 LC_COLLATE 'C' LC_CTYPE 'C';"
        & $psql -h localhost -p $porta -U postgres -d residuos_sinisa -v ON_ERROR_STOP=1 -q -f $dump
        Write-Host 'Banco restaurado.'
    }
    'psql' { & (Join-Path $bin 'psql.exe') -h localhost -p $porta -U postgres -d residuos_sinisa }
}
