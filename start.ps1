# KUBUKA - arranque de todos os servicos
# Uso: .\start.ps1

$ProjectDir = $PSScriptRoot

function Test-Port($port) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect("127.0.0.1", $port)
        $c.Close()
        return $true
    } catch { return $false }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   KUBUKA - Sistema de Pre-Seleccao" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. PostgreSQL ---
Write-Host "--- Base de dados ---" -ForegroundColor DarkGray
if (Test-Port 5432) {
    Write-Host "[OK] PostgreSQL a correr (porta 5432)" -ForegroundColor Green
} else {
    Write-Host "[FALHA] PostgreSQL nao encontrado na porta 5432" -ForegroundColor Red
    Write-Host "        Inicia com: Start-Service postgresql-x64-18" -ForegroundColor DarkYellow
    $continuar = Read-Host "Continuar mesmo assim? (s/n)"
    if ($continuar -ne "s") { exit 1 }
}

# --- 2. Ollama ---
Write-Host ""
Write-Host "--- Ollama (IA local) ---" -ForegroundColor DarkGray
if (Test-Port 11434) {
    Write-Host "[OK] Ollama a correr (porta 11434)" -ForegroundColor Green
} else {
    Write-Host "[ ] A iniciar Ollama..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 4
    if (Test-Port 11434) {
        Write-Host "[OK] Ollama iniciado" -ForegroundColor Green
    } else {
        Write-Host "[AVISO] Ollama nao arrancou - a analise de IA nao vai funcionar" -ForegroundColor DarkYellow
    }
}

# Modelos necessarios: llama3.2:1b (analise de CV, rapido) + qwen2.5:3b (scoring, mais preciso)
if (Test-Port 11434) {
    $models = ollama list 2>$null
    foreach ($model in @("llama3.2:1b", "qwen2.5:3b")) {
        if ($models -match [regex]::Escape($model)) {
            Write-Host "[OK] Modelo $model disponivel" -ForegroundColor Green
        } else {
            Write-Host "[ ] A descarregar $model (pode demorar alguns minutos)..." -ForegroundColor Yellow
            ollama pull $model
        }
    }
}

# --- 3. n8n ---
Write-Host ""
Write-Host "--- n8n (automacao) ---" -ForegroundColor DarkGray
if (Test-Port 5678) {
    Write-Host "[OK] n8n a correr (porta 5678)" -ForegroundColor Green
} else {
    Write-Host "[ ] A iniciar n8n numa nova janela..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd" -ArgumentList "/k n8n start" -WindowStyle Normal
    Start-Sleep -Seconds 25
    if (Test-Port 5678) {
        Write-Host "[OK] n8n iniciado" -ForegroundColor Green
    } else {
        Write-Host "[AVISO] n8n ainda nao respondeu - aguarda mais uns segundos" -ForegroundColor DarkYellow
    }
}

# --- 4. Django ---
Write-Host ""
Write-Host "--- Django ---" -ForegroundColor DarkGray
Set-Location $ProjectDir

$PythonExe = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[FALHA] Ambiente virtual .venv nao encontrado" -ForegroundColor Red
    Write-Host "        Cria com: python -m venv .venv" -ForegroundColor DarkYellow
    Write-Host "        Depois:    .venv\Scripts\activate && pip install -r requirements.txt" -ForegroundColor DarkYellow
    exit 1
}

Write-Host "[ ] A aplicar migracoes..." -ForegroundColor Yellow
$migrateOutput = & $PythonExe manage.py migrate 2>&1
$migrateOutput | Where-Object { $_ -match "Applying|No migrations|OK" } | ForEach-Object {
    Write-Host "    $_" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Tudo pronto!" -ForegroundColor Green
Write-Host ""
Write-Host "  Aplicacao -> http://localhost:8000" -ForegroundColor White
Write-Host "  Admin     -> http://localhost:8000/admin/" -ForegroundColor White
Write-Host "  n8n       -> http://localhost:5678" -ForegroundColor White
Write-Host "  Ollama    -> http://localhost:11434" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "A iniciar Django... (Ctrl+C para parar)" -ForegroundColor Yellow
Write-Host ""

& $PythonExe manage.py runserver
