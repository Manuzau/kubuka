<#
.SYNOPSIS
    Repoe a palavra-passe do superutilizador 'postgres' e cria a base de dados /
    utilizador do KUBUKA (kubuka_db / kubuka_user), sem precisares de saber
    a palavra-passe actual do postgres.

.DESCRIPTION
    Corre-se UMA VEZ, como Administrador, quando perdeste/desconheces a palavra-passe
    do utilizador 'postgres'. O script:
      1. Faz backup do pg_hba.conf
      2. Muda temporariamente a autenticacao local para 'trust' (sem password)
      3. Reinicia o servico do PostgreSQL e espera que fique pronto a aceitar ligacoes
      4. Define uma nova palavra-passe para 'postgres'
      5. Cria a role 'kubuka_user' (password 'kubuka_pass') e a base 'kubuka_db'
         (idempotente - nao falha se ja existirem)
      6. Restaura o pg_hba.conf original e reinicia o servico outra vez

.EXAMPLE
    # Numa PowerShell aberta como Administrador:
    .\scripts\setup_postgres.ps1
#>

[CmdletBinding()]
param(
    [string]$NewPostgresPassword,
    [string]$KubukaDbPassword = 'kubuka_pass'
)

$ErrorActionPreference = 'Stop'

function Assert-Admin {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        throw "Este script tem de correr numa PowerShell aberta como Administrador (botao direito -> 'Executar como administrador')."
    }
}

Assert-Admin

# --- Localizar instalacao do PostgreSQL -------------------------------------------------
$pgBaseDir = Join-Path ${env:ProgramFiles} 'PostgreSQL'
$pgRoot = Get-ChildItem $pgBaseDir -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1
if (-not $pgRoot) {
    throw "Nao encontrei uma instalacao do PostgreSQL em '$pgBaseDir'."
}
$psql = Join-Path $pgRoot.FullName "bin\psql.exe"
$pgIsReady = Join-Path $pgRoot.FullName "bin\pg_isready.exe"
$hbaPath = Join-Path $pgRoot.FullName "data\pg_hba.conf"
if (-not (Test-Path $psql))      { throw "psql.exe nao encontrado em $psql" }
if (-not (Test-Path $pgIsReady)) { throw "pg_isready.exe nao encontrado em $pgIsReady" }
if (-not (Test-Path $hbaPath))   { throw "pg_hba.conf nao encontrado em $hbaPath" }

$service = Get-Service | Where-Object { $_.DisplayName -like "*postgresql*" } | Select-Object -First 1
if (-not $service) { throw "Nao encontrei nenhum servico do PostgreSQL (Get-Service *postgresql*)." }

Write-Host "PostgreSQL: $($pgRoot.Name) | servico: $($service.Name)" -ForegroundColor Cyan

if (-not $NewPostgresPassword) {
    $secure = Read-Host "Define a NOVA palavra-passe para o utilizador 'postgres'" -AsSecureString
    $NewPostgresPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
}

function Wait-PgReady {
    param([int]$TimeoutSeconds = 30)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        & $pgIsReady -h 127.0.0.1 -p 5432 *> $null
        if ($LASTEXITCODE -eq 0) { return $true }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Sql-Escape {
    param([string]$Value)
    return $Value.Replace("'", "''")
}

function Invoke-Psql {
    param([Parameter(Mandatory)] [string]$Sql, [switch]$Quiet)
    $output = & $psql -U postgres -h 127.0.0.1 -v ON_ERROR_STOP=1 -c $Sql 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar SQL via psql (exit ${LASTEXITCODE}): $Sql`n$($output -join [Environment]::NewLine)"
    }
    if (-not $Quiet) { $output | ForEach-Object { Write-Host $_ } }
    return $output
}

function Invoke-PsqlScalar {
    param([Parameter(Mandatory)] [string]$Sql)
    $output = & $psql -U postgres -h 127.0.0.1 -tAc $Sql 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao consultar via psql (exit ${LASTEXITCODE}): $Sql`n$($output -join [Environment]::NewLine)"
    }
    if ($null -eq $output) { return '' }
    return (($output -join "`n")).Trim()
}

$escNewPgPwd = Sql-Escape $NewPostgresPassword
$escKubukaPwd = Sql-Escape $KubukaDbPassword

# --- Passo 1: backup + modo trust -------------------------------------------------------
$backupPath = "$hbaPath.kubuka-bak"
Copy-Item $hbaPath $backupPath -Force
Write-Host "Backup do pg_hba.conf em: $backupPath" -ForegroundColor DarkGray

try {
    (Get-Content $hbaPath) -replace '\bscram-sha-256\b', 'trust' -replace '\bmd5\b', 'trust' |
        Set-Content $hbaPath -Encoding ASCII

    Write-Host "Reiniciando $($service.Name) (modo trust temporario)..." -ForegroundColor Cyan
    Restart-Service $service.Name -Force

    if (-not (Wait-PgReady -TimeoutSeconds 30)) {
        throw "PostgreSQL nao ficou pronto a aceitar ligacoes 30s depois de reiniciar o servico. Verifica o log do PostgreSQL em '$($pgRoot.FullName)\data\log'."
    }
    Write-Host "PostgreSQL pronto a aceitar ligacoes (modo trust)." -ForegroundColor DarkGray

    $env:PGPASSWORD = ''

    # --- Passo 2: nova password do postgres ---------------------------------------------
    Invoke-Psql -Sql "ALTER USER postgres WITH PASSWORD '$escNewPgPwd';" | Out-Null
    Write-Host "Password do 'postgres' actualizada." -ForegroundColor Green

    # --- Passo 3: role + base de dados do KUBUKA (idempotente) --------------------------
    $roleExists = Invoke-PsqlScalar -Sql "SELECT 1 FROM pg_roles WHERE rolname='kubuka_user';"
    if ($roleExists -ne '1') {
        Invoke-Psql -Sql "CREATE ROLE kubuka_user LOGIN PASSWORD '$escKubukaPwd' CREATEDB;" | Out-Null
        Write-Host "Role 'kubuka_user' criada." -ForegroundColor Green
    } else {
        Invoke-Psql -Sql "ALTER ROLE kubuka_user WITH PASSWORD '$escKubukaPwd' CREATEDB;" | Out-Null
        Write-Host "Role 'kubuka_user' ja existia - password actualizada." -ForegroundColor Yellow
    }

    $dbExists = Invoke-PsqlScalar -Sql "SELECT 1 FROM pg_database WHERE datname='kubuka_db';"
    if ($dbExists -ne '1') {
        Invoke-Psql -Sql "CREATE DATABASE kubuka_db OWNER kubuka_user;" | Out-Null
        Write-Host "Base de dados 'kubuka_db' criada (owner: kubuka_user)." -ForegroundColor Green
    } else {
        Invoke-Psql -Sql "ALTER DATABASE kubuka_db OWNER TO kubuka_user;" | Out-Null
        Write-Host "Base de dados 'kubuka_db' ja existia - owner garantido." -ForegroundColor Yellow
    }
    Invoke-Psql -Sql "GRANT ALL PRIVILEGES ON DATABASE kubuka_db TO kubuka_user;" | Out-Null
}
finally {
    # --- Passo 4: restaurar autenticacao normal, sempre (mesmo se algo falhou acima) ----
    Copy-Item $backupPath $hbaPath -Force
    Write-Host "Reiniciando $($service.Name) (autenticacao normal restaurada)..." -ForegroundColor Cyan
    Restart-Service $service.Name -Force
    Wait-PgReady -TimeoutSeconds 30 | Out-Null
    $env:PGPASSWORD = $null
}

# --- Passo 5: verificacao final ----------------------------------------------------------
$env:PGPASSWORD = $KubukaDbPassword
& $psql -U kubuka_user -h 127.0.0.1 -d kubuka_db -c "SELECT current_user, current_database();"
$verifyExit = $LASTEXITCODE
$env:PGPASSWORD = $null

if ($verifyExit -ne 0) {
    throw "A ligacao final como kubuka_user falhou (exit $verifyExit). A autenticacao normal foi restaurada; reve a mensagem de erro acima."
}

Write-Host ""
Write-Host "Concluido." -ForegroundColor Green
Write-Host "  - Utilizador 'postgres': nova password definida (guarda-a nalgum lado seguro)."
Write-Host "  - kubuka_user / $KubukaDbPassword / kubuka_db : prontos a usar."
Write-Host ""
Write-Host "No .env do projecto, muda ou remove a linha:" -ForegroundColor Yellow
Write-Host "  DB_ENGINE=django.db.backends.sqlite3"
Write-Host "para usar o PostgreSQL (o settings.py deteta automaticamente se remover a linha)."
