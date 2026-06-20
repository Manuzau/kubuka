# start.ps1
# Arranca o KUBUKA completo: PostgreSQL, Ollama, n8n e Django
# Uso normal: .\start.ps1
# Para forcar reinicio dos servicos: .\start.ps1 -Force

param([switch]$Force)

$ProjectDir = $PSScriptRoot

function Test-Port($port) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect("127.0.0.1", $port)
        $c.Close()
        return $true
    } catch {
        return $false
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   KUBUKA - Sistema de Pre-Seleccao" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. POSTGRESQL ---
Write-Host "--- Base de Dados ---" -ForegroundColor DarkGray
if (Test-Port 5432) {
    Write-Host "[OK] PostgreSQL a correr na porta 5432" -ForegroundColor Green
} else {
    Write-Host "[!] PostgreSQL nao encontrado na porta 5432" -ForegroundColor Red
    Write-Host "    Tenta iniciar o servico PostgreSQL:" -ForegroundColor DarkYellow
    Write-Host "    net start postgresql-x64-14  (ou a versao instalada)" -ForegroundColor DarkGray
    Write-Host ""
    $continuar = Read-Host "Continuar sem PostgreSQL? (s/n)"
    if ($continuar -ne "s") {
        Write-Host "A sair. Inicia o PostgreSQL primeiro." -ForegroundColor Red
        exit 1
    }
    Write-Host "[AVISO] A continuar sem base de dados — o Django vai falhar ao iniciar." -ForegroundColor DarkYellow
}

# --- 2. OLLAMA ---
Write-Host ""
Write-Host "--- Inteligencia Artificial ---" -ForegroundColor DarkGray
if (Test-Port 11434) {
    Write-Host "[OK] Ollama a correr na porta 11434" -ForegroundColor Green
} else {
    Write-Host "[ ] A iniciar Ollama..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 4
    if (Test-Port 11434) {
        Write-Host "[OK] Ollama iniciado" -ForegroundColor Green
    } else {
        Write-Host "[AVISO] Ollama nao respondeu — o sistema arranca sem analise de IA" -ForegroundColor DarkYellow
    }
}

# Verificar se o modelo esta disponivel (llama3.2 por defeito)
$ollamaModel = "llama3.2"
if (Test-Port 11434) {
    $models = ollama list 2>$null
    if ($models -match "llama3.2") {
        Write-Host "[OK] Modelo $ollamaModel disponivel" -ForegroundColor Green
    } else {
        Write-Host "[ ] Modelo $ollamaModel nao encontrado — a fazer download (pode demorar)..." -ForegroundColor Yellow
        Write-Host "    Nota: para usar modelo cloud, muda OLLAMA_MODEL no .env" -ForegroundColor DarkGray
        ollama pull llama3.2
    }
}

# --- 3. N8N ---
Write-Host ""
Write-Host "--- Automacao ---" -ForegroundColor DarkGray
if (Test-Port 5678) {
    Write-Host "[OK] n8n a correr na porta 5678" -ForegroundColor Green
} else {
    Write-Host "[ ] A abrir n8n numa nova janela..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd" -ArgumentList "/k n8n start" -WindowStyle Normal
    Write-Host "    (aguarda que o n8n carregue em http://localhost:5678)" -ForegroundColor DarkGray
    Start-Sleep -Seconds 5
}

# --- 4. DJANGO ---
Write-Host ""
Write-Host "--- Aplicacao Django ---" -ForegroundColor DarkGray
Set-Location $ProjectDir

# Usar sempre o Python do ambiente virtual do projecto
$PythonExe = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[!] Ambiente virtual nao encontrado em .venv\" -ForegroundColor Red
    Write-Host "    Cria-o com: python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt" -ForegroundColor DarkYellow
    exit 1
}

Write-Host "[ ] A verificar migracoes..." -ForegroundColor Yellow
$migrateOutput = & $PythonExe manage.py migrate 2>&1
$migrateOutput | Where-Object { $_ -match "Applying|No migrations|OK" } | ForEach-Object {
    Write-Host "    $_" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Tudo pronto!" -ForegroundColor Green
Write-Host ""
Write-Host "  Aplicacao  -> http://localhost:8000" -ForegroundColor White
Write-Host "  n8n        -> http://localhost:5678" -ForegroundColor White
Write-Host "  Ollama     -> http://localhost:11434" -ForegroundColor White
Write-Host "  Admin      -> http://localhost:8000/admin/" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "A iniciar... (Ctrl+C para parar)" -ForegroundColor Yellow
Write-Host ""

& $PythonExe manage.py runserver
