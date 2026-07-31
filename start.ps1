# KUBUKA - arranque dinamico de todos os servicos
# Uso: .\start.ps1
#
# Funciona tanto no dia-a-dia (tudo ja instalado - arranca em poucos segundos) como
# numa maquina nova (deteta o que falta e instala sozinho via winget, sem perguntar).
# Se algo nao puder ser automatizado (ex: winget indisponivel, UAC recusado), o script
# avisa claramente e diz o que fazer a seguir - nunca falha em silencio.

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

function Test-Port($port) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect("127.0.0.1", $port)
        $c.Close()
        return $true
    } catch { return $false }
}

function Update-SessionPath {
    # Depois de um "winget install", o instalador actualiza o PATH do sistema/utilizador,
    # mas esta sessao do PowerShell continua com o PATH antigo em memoria. Sem isto, um
    # programa instalado agora só ficaria visivel depois de reabrir o terminal.
    $machinePath = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath    = [System.Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machinePath;$userPath"
}

$script:WingetChecked = $false
$script:WingetOk = $false

function Test-Winget {
    if ($script:WingetChecked) { return $script:WingetOk }
    $script:WingetChecked = $true
    $script:WingetOk = [bool](Get-Command winget -ErrorAction SilentlyContinue)
    if (-not $script:WingetOk) {
        Write-Host "[AVISO] 'winget' nao disponivel neste computador." -ForegroundColor DarkYellow
        Write-Host "        Actualiza a app 'App Installer' na Microsoft Store para poderes instalar" -ForegroundColor DarkYellow
        Write-Host "        dependencias automaticamente, ou segue a instalacao manual no README." -ForegroundColor DarkYellow
    }
    return $script:WingetOk
}

function Install-ViaWinget {
    param(
        [Parameter(Mandatory)] [string]$Id,
        [Parameter(Mandatory)] [string]$FriendlyName
    )
    if (-not (Test-Winget)) { return $false }
    Write-Host "[ ] A instalar $FriendlyName via winget (pode demorar alguns minutos)..." -ForegroundColor Yellow
    try {
        winget install --id $Id -e --silent --accept-package-agreements --accept-source-agreements | Out-Null
    } catch {
        Write-Host "[FALHA] Erro ao instalar ${FriendlyName}: $_" -ForegroundColor Red
        return $false
    }
    Update-SessionPath
    Write-Host "[OK] $FriendlyName instalado." -ForegroundColor Green
    return $true
}

function Ensure-Command {
    param(
        [Parameter(Mandatory)] [string]$Command,
        [Parameter(Mandatory)] [string]$FriendlyName,
        [string]$WingetId
    )
    if (Get-Command $Command -ErrorAction SilentlyContinue) { return $true }

    Write-Host "[ ] $FriendlyName nao encontrado." -ForegroundColor Yellow
    if ($WingetId) {
        if (Install-ViaWinget -Id $WingetId -FriendlyName $FriendlyName) {
            if (Get-Command $Command -ErrorAction SilentlyContinue) { return $true }
            Write-Host "[AVISO] $FriendlyName instalado mas ainda nao aparece nesta sessao do terminal." -ForegroundColor DarkYellow
            Write-Host "        Fecha e reabre o terminal, depois corre '.\start.ps1' outra vez." -ForegroundColor DarkYellow
            return $false
        }
    }
    Write-Host "[FALHA] Nao consegui garantir $FriendlyName. Ve a seccao 'Instalacao de raiz' do README." -ForegroundColor Red
    return $false
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   KUBUKA - Sistema de Pre-Seleccao" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Le AI_PROVIDER cedo (do .env se ja existir) para decidir se vale a pena mexer no Ollama.
# Sem .env ainda (1a execucao), assume "local" - o valor por omissao do .env.example.
$EnvFileEarly = Join-Path $ProjectDir ".env"
$AiProviderEarly = "local"
if (Test-Path $EnvFileEarly) {
    Get-Content $EnvFileEarly | ForEach-Object {
        if ($_ -match '^\s*AI_PROVIDER\s*=\s*(.+)$') { $AiProviderEarly = $Matches[1].Trim() }
    }
}
$UsesOllama = ($AiProviderEarly -ne "cloud")

# --- 1. Ferramentas base ---------------------------------------------------------------
Write-Host ""
Write-Host "--- Ferramentas base ---" -ForegroundColor DarkGray

$HasPython = Ensure-Command -Command "python" -FriendlyName "Python" -WingetId "Python.Python.3.12"
if (-not $HasPython) {
    Write-Host ""
    Write-Host "[FALHA] Sem Python nao e possivel continuar." -ForegroundColor Red
    exit 1
}
$HasNode = Ensure-Command -Command "node" -FriendlyName "Node.js" -WingetId "OpenJS.NodeJS.LTS"

if ($UsesOllama) {
    $HasOllamaBin = Ensure-Command -Command "ollama" -FriendlyName "Ollama" -WingetId "Ollama.Ollama"
} else {
    # AI_PROVIDER=cloud - usa-se a Groq, nao forcamos a instalacao do Ollama (~2GB+ de
    # modelos). Se ja estiver instalado por outro motivo, continua a poder ser usado como
    # rede de seguranca automatica no n8n caso a Groq falhe (ver workflows).
    $HasOllamaBin = [bool](Get-Command ollama -ErrorAction SilentlyContinue)
    if ($HasOllamaBin) {
        Write-Host "[OK] Ollama encontrado (nao obrigatorio com AI_PROVIDER=cloud, mas fica disponivel como fallback)" -ForegroundColor Green
    } else {
        Write-Host "[ ] Ollama nao instalado - normal com AI_PROVIDER=cloud (a usar a Groq)." -ForegroundColor DarkGray
    }
}

if ($HasNode -and -not (Get-Command n8n -ErrorAction SilentlyContinue)) {
    Write-Host "[ ] n8n nao encontrado - a instalar via npm (pode demorar 1-2 min)..." -ForegroundColor Yellow
    npm install -g n8n --silent 2>&1 | Out-Null
    Update-SessionPath
    if (Get-Command n8n -ErrorAction SilentlyContinue) {
        Write-Host "[OK] n8n instalado." -ForegroundColor Green
    } else {
        Write-Host "[AVISO] Falha a instalar o n8n - a automacao/IA nao vai funcionar." -ForegroundColor DarkYellow
    }
}
$HasN8n = [bool](Get-Command n8n -ErrorAction SilentlyContinue)

# --- 2. Ambiente Python (venv + dependencias) ------------------------------------------
Write-Host ""
Write-Host "--- Ambiente Python ---" -ForegroundColor DarkGray

$VenvPath  = Join-Path $ProjectDir ".venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "[ ] A criar o ambiente virtual (.venv)..." -ForegroundColor Yellow
    python -m venv $VenvPath
}

if (-not (Test-Path $PythonExe)) {
    Write-Host "[FALHA] Nao foi possivel criar o .venv." -ForegroundColor Red
    exit 1
}

$ReqFile     = Join-Path $ProjectDir "requirements.txt"
$ReqHashFile = Join-Path $VenvPath ".reqs_hash"
$CurrentHash = (Get-FileHash -Path $ReqFile -Algorithm SHA256).Hash
$PreviousHash = $null
if (Test-Path $ReqHashFile) { $PreviousHash = (Get-Content $ReqHashFile -Raw).Trim() }

if ($CurrentHash -ne $PreviousHash) {
    Write-Host "[ ] A instalar dependencias Python (1a vez, ou requirements.txt mudou)..." -ForegroundColor Yellow
    & $PythonExe -m pip install --quiet --upgrade pip
    & $PythonExe -m pip install --quiet -r $ReqFile
    if ($LASTEXITCODE -eq 0) {
        Set-Content -Path $ReqHashFile -Value $CurrentHash -NoNewline
        Write-Host "[OK] Dependencias instaladas." -ForegroundColor Green
    } else {
        Write-Host "[AVISO] 'pip install' terminou com erros - revê acima." -ForegroundColor DarkYellow
    }
} else {
    Write-Host "[OK] Dependencias Python ja atualizadas." -ForegroundColor Green
}

# --- 3. Configuracao (.env) -------------------------------------------------------------
Write-Host ""
Write-Host "--- Configuracao (.env) ---" -ForegroundColor DarkGray

$EnvFile = Join-Path $ProjectDir ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "[ ] .env nao encontrado - a criar a partir de .env.example..." -ForegroundColor Yellow
    Copy-Item (Join-Path $ProjectDir ".env.example") $EnvFile

    $secretKey = & $PythonExe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
    $envLines = Get-Content $EnvFile -Encoding UTF8
    $envLines = $envLines | ForEach-Object {
        if ($_ -match '^\s*SECRET_KEY\s*=') { "SECRET_KEY=$secretKey" } else { $_ }
    }
    [System.IO.File]::WriteAllLines($EnvFile, $envLines, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "[OK] .env criado com uma SECRET_KEY unica para esta instalacao." -ForegroundColor Green
} else {
    Write-Host "[OK] .env ja existe." -ForegroundColor Green
}

# --- 4. Base de dados (PostgreSQL) -------------------------------------------------------
Write-Host ""
Write-Host "--- Base de dados (PostgreSQL) ---" -ForegroundColor DarkGray

$pgService = Get-Service | Where-Object { $_.DisplayName -like "*postgresql*" } | Select-Object -First 1
if (-not $pgService) {
    Write-Host "[ ] PostgreSQL nao encontrado - a instalar..." -ForegroundColor Yellow
    Install-ViaWinget -Id "PostgreSQL.PostgreSQL.16" -FriendlyName "PostgreSQL" | Out-Null
    Start-Sleep -Seconds 5
    $pgService = Get-Service | Where-Object { $_.DisplayName -like "*postgresql*" } | Select-Object -First 1
}

if ($pgService) {
    if ($pgService.StartType -ne "Automatic") {
        try { Set-Service -Name $pgService.Name -StartupType Automatic } catch {}
    }
    if ($pgService.Status -ne "Running") {
        try { Start-Service -Name $pgService.Name; Start-Sleep -Seconds 3 } catch {}
    }
}

function Test-KubukaDb {
    # Usa psycopg2 (o mesmo driver que o Django usa) em vez do binario 'psql' -
    # este ultimo pode nao estar no PATH mesmo com o PostgreSQL a funcionar bem.
    $checkScript = Join-Path $ProjectDir "scripts\check_postgres.py"
    $result = & $PythonExe $checkScript 2>$null
    return ($result -match "^OK$")
}

if (Test-Port 5432) {
    Write-Host "[OK] PostgreSQL a correr (porta 5432)" -ForegroundColor Green

    $psqlOk = Test-KubukaDb

    if ($psqlOk) {
        Write-Host "[OK] Base de dados 'kubuka_db' pronta" -ForegroundColor Green
    } else {
        Write-Host "[ ] Base/utilizador do KUBUKA em falta - a configurar automaticamente..." -ForegroundColor Yellow
        Write-Host "    (pode pedir permissao de Administrador uma vez - janela UAC)" -ForegroundColor DarkGray

        $setupScript = Join-Path $ProjectDir "scripts\setup_postgres.ps1"
        $bootstrapPwd = "Kubuka_PG_Setup_2026"
        try {
            Start-Process powershell -Verb RunAs -Wait -ArgumentList @(
                "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$setupScript`"",
                "-NewPostgresPassword", "`"$bootstrapPwd`"", "-KubukaDbPassword", "`"kubuka_pass`""
            )
        } catch {
            Write-Host "[AVISO] Nao foi possivel elevar privilegios (UAC recusado?)." -ForegroundColor DarkYellow
        }

        $psqlOk = Test-KubukaDb

        if ($psqlOk) {
            Write-Host "[OK] Base de dados configurada automaticamente." -ForegroundColor Green
        } else {
            Write-Host "[AVISO] Nao consegui configurar o PostgreSQL automaticamente." -ForegroundColor DarkYellow
            Write-Host "        Sem problema: o Django deteta isto sozinho e usa SQLite em vez" -ForegroundColor DarkGray
            Write-Host "        (ver core/settings.py) - a app continua a funcionar na mesma." -ForegroundColor DarkGray
            Write-Host "        Para usar PostgreSQL, ve o Passo 8 do README." -ForegroundColor DarkGray
        }
    }
} else {
    Write-Host "[AVISO] PostgreSQL nao arrancou - o Django vai usar SQLite automaticamente." -ForegroundColor DarkYellow
}

# --- 5. Ollama (IA local) ----------------------------------------------------------------
Write-Host ""
Write-Host "--- Ollama (IA local) ---" -ForegroundColor DarkGray

if ($HasOllamaBin) {
    if (Test-Port 11434) {
        Write-Host "[OK] Ollama a correr (porta 11434)" -ForegroundColor Green
    } else {
        Write-Host "[ ] A iniciar Ollama..." -ForegroundColor Yellow
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Minimized -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 4
        if (Test-Port 11434) {
            Write-Host "[OK] Ollama iniciado" -ForegroundColor Green
        } elseif ($UsesOllama) {
            Write-Host "[AVISO] Ollama nao arrancou - a analise de IA local nao vai funcionar" -ForegroundColor DarkYellow
            Write-Host "        (a Groq na cloud continua a funcionar como alternativa, se configurada)" -ForegroundColor DarkGray
        }
    }

    if ($UsesOllama -and (Test-Port 11434)) {
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
} elseif ($UsesOllama) {
    Write-Host "[AVISO] Ollama nao instalado - a analise de IA local nao vai funcionar." -ForegroundColor DarkYellow
    Write-Host "        (a Groq na cloud continua a funcionar como alternativa, se configurada)" -ForegroundColor DarkGray
}

# --- 6. n8n (automacao) -------------------------------------------------------------------
Write-Host ""
Write-Host "--- n8n (automacao) ---" -ForegroundColor DarkGray

if ($HasN8n) {
    # Le AI_PROVIDER e GROQ_API_KEY do .env para os passar ao processo do n8n
    # (o n8n corre a parte do Django, por isso nao le o .env do Django automaticamente).
    $AiProvider = "local"
    $GroqApiKey = ""
    if (Test-Path $EnvFile) {
        Get-Content $EnvFile | ForEach-Object {
            if ($_ -match '^\s*AI_PROVIDER\s*=\s*(.+)$')  { $AiProvider = $Matches[1].Trim() }
            if ($_ -match '^\s*GROQ_API_KEY\s*=\s*(.+)$')  { $GroqApiKey = $Matches[1].Trim() }
        }
    }
    if ($AiProvider -eq "cloud" -and [string]::IsNullOrWhiteSpace($GroqApiKey)) {
        Write-Host "[AVISO] AI_PROVIDER=cloud mas GROQ_API_KEY esta vazio no .env" -ForegroundColor DarkYellow
        Write-Host "        Corre: .\scripts\set_groq_key.ps1" -ForegroundColor DarkGray
    }
    $env:AI_PROVIDER = $AiProvider
    $env:GROQ_API_KEY = $GroqApiKey
    $env:N8N_BLOCK_ENV_ACCESS_IN_NODE = "false"   # necessario para os workflows lerem $env.AI_PROVIDER / $env.GROQ_API_KEY
    Write-Host "    Motor de IA: $AiProvider" -ForegroundColor DarkGray

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

    if (Test-Port 5678) {
        # Verificacao read-only directamente na BD do n8n - nao escreve nada aqui.
        $n8nDb = Join-Path $env:USERPROFILE ".n8n\database.sqlite"
        if (Test-Path $n8nDb) {
            $result = & $PythonExe (Join-Path $ProjectDir "scripts\check_n8n_status.py") $n8nDb 2>$null
            if ($result -match '^(\d+),(\d+)$') {
                $userCount = [int]$Matches[1]
                $wfCount = [int]$Matches[2]
                if ($userCount -eq 0) {
                    Write-Host "[ ] 1a vez a usar este n8n - falta criar a conta inicial." -ForegroundColor Yellow
                    Write-Host "    A abrir http://localhost:5678 no browser - cria a conta e depois:" -ForegroundColor DarkGray
                    Write-Host "    Workflows -> Import from File -> importa n8n_workflow_kubuka.json" -ForegroundColor DarkGray
                    Write-Host "    e n8n_workflow_job_scoring.json (raiz do projecto), activa ambos." -ForegroundColor DarkGray
                    Start-Process "http://localhost:5678"
                } elseif ($wfCount -eq 0) {
                    Write-Host "[ ] Workflows do KUBUKA ainda nao importados." -ForegroundColor Yellow
                    Write-Host "    A abrir http://localhost:5678 no browser ->" -ForegroundColor DarkGray
                    Write-Host "    Workflows -> Import from File -> importa n8n_workflow_kubuka.json" -ForegroundColor DarkGray
                    Write-Host "    e n8n_workflow_job_scoring.json (raiz do projecto), activa ambos." -ForegroundColor DarkGray
                    Start-Process "http://localhost:5678"
                } else {
                    Write-Host "[OK] Workflows do KUBUKA presentes no n8n" -ForegroundColor Green
                }
            }
        }
    }
} else {
    Write-Host "[AVISO] n8n nao disponivel - upload de CV e candidaturas nao vao accionar a IA." -ForegroundColor DarkYellow
}

# --- 7. Django ------------------------------------------------------------------------
Write-Host ""
Write-Host "--- Django ---" -ForegroundColor DarkGray

Write-Host "[ ] A aplicar migracoes..." -ForegroundColor Yellow
$migrateOutput = & $PythonExe manage.py migrate 2>&1
$migrateOutput | Where-Object { $_ -match "Applying|No migrations|OK" } | ForEach-Object {
    Write-Host "    $_" -ForegroundColor DarkGray
}

$AdminUser = "admin"
$AdminPass = "Kubuka#Demo2026"
$superuserResult = & $PythonExe (Join-Path $ProjectDir "scripts\ensure_default_superuser.py") 2>&1
if ($superuserResult -match "CREATED") {
    Write-Host "[OK] Superutilizador por omissao criado." -ForegroundColor Green
} elseif ($superuserResult -notmatch "EXISTS") {
    Write-Host "[AVISO] Nao consegui confirmar/criar um superutilizador: $superuserResult" -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Tudo pronto!" -ForegroundColor Green
Write-Host ""
Write-Host "  Aplicacao -> http://localhost:8000" -ForegroundColor White
Write-Host "  Admin     -> http://localhost:8000/admin/  ($AdminUser / $AdminPass)" -ForegroundColor White
Write-Host "  n8n       -> http://localhost:5678" -ForegroundColor White
Write-Host "  Ollama    -> http://localhost:11434" -ForegroundColor White
Write-Host ""
Write-Host "  Chave Groq esgotada? .\scripts\set_groq_key.ps1" -ForegroundColor DarkGray
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "A iniciar Django... (Ctrl+C para parar)" -ForegroundColor Yellow
Write-Host ""

& $PythonExe manage.py runserver
