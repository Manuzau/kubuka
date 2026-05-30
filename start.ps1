# start.ps1 - Arranca todos os servicos do KUBUKA
# Uso: .\start.ps1

param([switch]$Force)

$ProjectDir = $PSScriptRoot

function Test-Port($port) {
    try {
        $conn = New-Object System.Net.Sockets.TcpClient
        $conn.Connect("127.0.0.1", $port)
        $conn.Close()
        return $true
    } catch { return $false }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  KUBUKA - Iniciar todos os servicos" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. OLLAMA ---
if (Test-Port 11434) {
    Write-Host "[OK] Ollama ja esta a correr (porta 11434)" -ForegroundColor Green
} else {
    Write-Host "[ ] A iniciar Ollama..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
    if (Test-Port 11434) {
        Write-Host "[OK] Ollama iniciado" -ForegroundColor Green
    } else {
        Write-Host "[AVISO] Ollama nao respondeu - sistema funciona sem IA (modo degradado)" -ForegroundColor DarkYellow
    }
}

# --- 2. N8N ---
if (Test-Port 5678) {
    Write-Host "[OK] n8n ja esta a correr (porta 5678)" -ForegroundColor Green
} else {
    Write-Host "[ ] A iniciar n8n numa nova janela..." -ForegroundColor Yellow
    Start-Process -FilePath "cmd" -ArgumentList "/k n8n start" -WindowStyle Normal
    Write-Host "    (aguarda que o n8n abra no browser em http://localhost:5678)" -ForegroundColor DarkGray
    Start-Sleep -Seconds 5
}

# --- 3. DJANGO ---
Write-Host ""
Write-Host "[ ] A aplicar migracoes..." -ForegroundColor Yellow
Set-Location $ProjectDir
python manage.py migrate 2>&1 | Where-Object { $_ -match "Applying|No migrations" }

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Sistema pronto!" -ForegroundColor Green
Write-Host ""
Write-Host "  Django  -> http://localhost:8000" -ForegroundColor White
Write-Host "  n8n     -> http://localhost:5678" -ForegroundColor White
Write-Host "  Ollama  -> http://localhost:11434" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "A iniciar Django (Ctrl+C para parar)..." -ForegroundColor Yellow
Write-Host ""

python manage.py runserver
