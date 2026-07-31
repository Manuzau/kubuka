<#
.SYNOPSIS
    Troca a GROQ_API_KEY no .env e reinicia o n8n para a chave nova entrar em vigor
    imediatamente (o n8n só lê variáveis de ambiente no arranque do processo).

.DESCRIPTION
    Útil quando a chave Groq actual esgota as chamadas gratuitas (ex: trocaste de
    conta/email na consola da Groq) - evita ter de editar o .env à mão e lembrar de
    reiniciar o n8n manualmente.

.EXAMPLE
    .\scripts\set_groq_key.ps1 -Key "gsk_a-tua-chave-nova-aqui"

.EXAMPLE
    # Sem -Key, o script pergunta interactivamente
    .\scripts\set_groq_key.ps1
#>

param(
    [string]$Key,
    [switch]$NoRestart
)

$ErrorActionPreference = 'Stop'
$ProjectDir = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $ProjectDir ".env"

if (-not (Test-Path $EnvFile)) {
    Write-Host "[FALHA] .env nao encontrado em $EnvFile" -ForegroundColor Red
    Write-Host "        Corre primeiro: copy .env.example .env" -ForegroundColor DarkYellow
    exit 1
}

if (-not $Key) {
    $Key = Read-Host "Cola a nova GROQ_API_KEY (de https://console.groq.com/keys)"
}
$Key = $Key.Trim()
if (-not $Key) {
    Write-Host "[FALHA] Nenhuma chave introduzida." -ForegroundColor Red
    exit 1
}

# --- Actualizar (ou adicionar) a linha GROQ_API_KEY= no .env, preservando o resto ---
$lines = Get-Content -Path $EnvFile -Encoding UTF8
$found = $false
$newLines = foreach ($line in $lines) {
    if ($line -match '^\s*GROQ_API_KEY\s*=') {
        $found = $true
        "GROQ_API_KEY=$Key"
    } else {
        $line
    }
}
if (-not $found) {
    $newLines += "GROQ_API_KEY=$Key"
}
# -Encoding UTF8 do PowerShell 5.1 escreve com BOM; o django-environ le sem problemas,
# mas usamos .NET directamente para escrever sem BOM e manter o ficheiro identico ao original.
[System.IO.File]::WriteAllLines($EnvFile, $newLines, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "[OK] GROQ_API_KEY actualizada no .env." -ForegroundColor Green

if ($NoRestart) {
    Write-Host "Lembra-te de reiniciar o n8n (.\start.ps1) para a chave nova entrar em vigor." -ForegroundColor DarkYellow
    exit 0
}

# --- Reiniciar o n8n para o processo carregar a variavel de ambiente nova ---
function Test-Port($port) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect("127.0.0.1", $port)
        $c.Close()
        return $true
    } catch { return $false }
}

if (Test-Port 5678) {
    Write-Host "[ ] A parar o n8n para aplicar a chave nova..." -ForegroundColor Yellow
    Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*n8n*' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
}

$AiProvider = "local"
$GroqApiKey = $Key
(Get-Content -Path $EnvFile -Encoding UTF8) | ForEach-Object {
    if ($_ -match '^\s*AI_PROVIDER\s*=\s*(.+)$') { $AiProvider = $Matches[1].Trim() }
}
$env:AI_PROVIDER = $AiProvider
$env:GROQ_API_KEY = $GroqApiKey
$env:N8N_BLOCK_ENV_ACCESS_IN_NODE = "false"

Write-Host "[ ] A reiniciar o n8n numa nova janela..." -ForegroundColor Yellow
Start-Process -FilePath "cmd" -ArgumentList "/k n8n start" -WindowStyle Normal
Start-Sleep -Seconds 20
if (Test-Port 5678) {
    Write-Host "[OK] n8n reiniciado com a nova chave Groq." -ForegroundColor Green
} else {
    Write-Host "[AVISO] n8n ainda nao respondeu - aguarda mais uns segundos ou verifica a janela aberta." -ForegroundColor DarkYellow
}
