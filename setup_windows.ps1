param(
    [switch]$ForceConfig,
    [switch]$SkipToolInstall,
    [switch]$SkipPiperDownload,
    [switch]$SkipOllamaPull,
    [string]$OllamaModel = "llama3.1:8b",
    [string]$PiperVoice = "en_US-lessac-medium"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $Root ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$PiperDir = Join-Path $Root "voices\piper"
$PiperExe = Join-Path $PiperDir "piper.exe"
$PiperVoiceDir = Join-Path $PiperDir "voices"
$VoiceModel = Join-Path $PiperVoiceDir "$PiperVoice.onnx"
$VoiceConfig = Join-Path $PiperVoiceDir "$PiperVoice.onnx.json"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "OK  $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "WARN $Message" -ForegroundColor Yellow
}

function Test-Command {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Refresh-Path {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $Root
    )

    Write-Host "RUN $FilePath $($Arguments -join ' ')"
    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -NoNewWindow -Wait -PassThru

    if ($process.ExitCode -ne 0) {
        throw "$FilePath exited with code $($process.ExitCode)"
    }
}

function Install-WithWinget {
    param(
        [string]$CommandName,
        [string]$PackageId
    )

    if (Test-Command $CommandName) {
        Write-Ok "$CommandName is already installed"
        return
    }

    if ($SkipToolInstall) {
        Write-Warn "$CommandName is missing. Install package '$PackageId' manually, then rerun this script."
        return
    }

    if (-not (Test-Command "winget")) {
        Write-Warn "winget is not available. Install $CommandName manually, then rerun this script."
        return
    }

    Write-Step "Installing $CommandName with winget"
    Invoke-Checked "winget" @(
        "install",
        "--id", $PackageId,
        "--exact",
        "--silent",
        "--accept-package-agreements",
        "--accept-source-agreements"
    )
    Refresh-Path
}

function Get-PythonLauncher {
    if (Test-Command "py") {
        return @{ File = "py"; Args = @("-3.11") }
    }

    if (Test-Command "python") {
        return @{ File = "python"; Args = @() }
    }

    if (-not $SkipToolInstall -and (Test-Command "winget")) {
        Write-Step "Installing Python 3.11 with winget"
        Invoke-Checked "winget" @(
            "install",
            "--id", "Python.Python.3.11",
            "--exact",
            "--silent",
            "--accept-package-agreements",
            "--accept-source-agreements"
        )
        Refresh-Path
    }

    if (Test-Command "py") {
        return @{ File = "py"; Args = @("-3.11") }
    }

    if (Test-Command "python") {
        return @{ File = "python"; Args = @() }
    }

    throw "Python 3.11+ is required. Install Python, then rerun this script."
}

function Copy-Template {
    param(
        [string]$Template,
        [string]$Target
    )

    if ((Test-Path $Target) -and -not $ForceConfig) {
        Write-Ok "$(Split-Path -Leaf $Target) already exists"
        return
    }

    Copy-Item -LiteralPath $Template -Destination $Target -Force
    Write-Ok "Created $(Split-Path -Leaf $Target)"
}

function Download-File {
    param(
        [string]$Url,
        [string]$Destination
    )

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    Write-Host "GET $Url"
    Invoke-WebRequest -Uri $Url -OutFile $Destination
}

function Install-Piper {
    if ($SkipPiperDownload) {
        Write-Warn "Skipping Piper download"
        return
    }

    if (-not (Test-Path $PiperExe)) {
        Write-Step "Downloading Piper"
        $release = Invoke-RestMethod -Uri "https://api.github.com/repos/rhasspy/piper/releases/latest"
        $asset = $release.assets |
            Where-Object { $_.name -match "windows.*(amd64|x86_64).*\.zip$" } |
            Select-Object -First 1

        if (-not $asset) {
            throw "Could not find a Windows amd64 Piper release asset."
        }

        $zipPath = Join-Path $env:TEMP $asset.name
        Download-File -Url $asset.browser_download_url -Destination $zipPath

        $extractDir = Join-Path $env:TEMP ("piper-" + [Guid]::NewGuid().ToString("N"))
        Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir -Force

        $downloadedPiper = Get-ChildItem -Path $extractDir -Recurse -Filter "piper.exe" | Select-Object -First 1
        if (-not $downloadedPiper) {
            throw "Downloaded Piper archive did not contain piper.exe."
        }

        New-Item -ItemType Directory -Force -Path $PiperDir | Out-Null
        Copy-Item -Path (Join-Path $downloadedPiper.DirectoryName "*") -Destination $PiperDir -Recurse -Force
        Write-Ok "Installed Piper to $PiperDir"
    } else {
        Write-Ok "Piper is already installed"
    }

    if ((Test-Path $VoiceModel) -and (Test-Path $VoiceConfig)) {
        Write-Ok "Piper voice $PiperVoice is already installed"
        return
    }

    Write-Step "Downloading Piper voice $PiperVoice"
    $parts = $PiperVoice -split "-"
    if ($parts.Count -lt 3) {
        throw "Unexpected Piper voice name '$PiperVoice'. Expected format like en_US-lessac-medium."
    }

    $locale = $parts[0]
    $speaker = $parts[1]
    $quality = $parts[2]
    $baseUrl = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/$locale/$speaker/$quality/$PiperVoice"

    Download-File -Url "$baseUrl.onnx" -Destination $VoiceModel
    Download-File -Url "$baseUrl.onnx.json" -Destination $VoiceConfig
    Write-Ok "Installed Piper voice $PiperVoice"
}

function Update-LocalConfig {
    $configPath = Join-Path $Root "config.json"
    $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json

    $config.paths.piper_exe = ($PiperExe -replace "\\", "/")
    $config.paths.voice_model = ($VoiceModel -replace "\\", "/")
    $config.paths.voice_config = ($VoiceConfig -replace "\\", "/")
    $config.paths.ffmpeg = "ffmpeg"
    $config.paths.ffprobe = "ffprobe"

    $json = $config | ConvertTo-Json -Depth 20
    Set-Content -LiteralPath $configPath -Value $json -Encoding UTF8
    Write-Ok "Updated config.json Piper and FFmpeg paths"
}

function Update-LocalEnv {
    $envPath = Join-Path $Root ".env"
    $content = Get-Content -LiteralPath $envPath -Raw

    if ($content -match "(?m)^OLLAMA_MODEL=") {
        $content = $content -replace "(?m)^OLLAMA_MODEL=.*$", "OLLAMA_MODEL=$OllamaModel"
    } else {
        $content = $content.TrimEnd() + "`r`nOLLAMA_MODEL=$OllamaModel`r`n"
    }

    Set-Content -LiteralPath $envPath -Value $content -Encoding UTF8
    Write-Ok "Updated .env Ollama model"
}

function Start-OllamaIfNeeded {
    try {
        Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 | Out-Null
        Write-Ok "Ollama server is already running"
        return
    } catch {
        Write-Step "Starting Ollama server"
        Start-Process -FilePath "ollama" -ArgumentList @("serve") -WindowStyle Hidden
        Start-Sleep -Seconds 5
    }
}

Push-Location $Root
try {
    Write-Step "Finance Shorts Factory setup"
    Write-Host "Project root: $Root"

    Write-Step "Checking system tools"
    Install-WithWinget -CommandName "git" -PackageId "Git.Git"
    Install-WithWinget -CommandName "ffmpeg" -PackageId "Gyan.FFmpeg"
    Install-WithWinget -CommandName "ollama" -PackageId "Ollama.Ollama"

    $pythonLauncher = Get-PythonLauncher

    Write-Step "Creating virtual environment"
    if (-not (Test-Path $VenvPython)) {
        Invoke-Checked $pythonLauncher.File ($pythonLauncher.Args + @("-m", "venv", ".venv"))
    } else {
        Write-Ok ".venv already exists"
    }

    Write-Step "Installing Python dependencies"
    Invoke-Checked $VenvPython @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-Checked $VenvPython @("-m", "pip", "install", "-r", "requirements.txt")
    Invoke-Checked $VenvPython @("-m", "pip", "install", "ruff", "bandit")

    Write-Step "Creating local config files"
    Copy-Template -Template (Join-Path $Root ".env.example") -Target (Join-Path $Root ".env")
    Copy-Template -Template (Join-Path $Root "config.example.json") -Target (Join-Path $Root "config.json")
    Update-LocalEnv

    Write-Step "Installing Piper"
    Install-Piper
    Update-LocalConfig

    Write-Step "Preparing local folders"
    New-Item -ItemType Directory -Force -Path (Join-Path $Root "outputs") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $Root "assets\backgrounds\default") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $Root "assets\music\library") | Out-Null

    if (-not $SkipOllamaPull) {
        Write-Step "Preparing Ollama model $OllamaModel"
        if (-not (Test-Command "ollama")) {
            throw "Ollama is not available. Install Ollama, then rerun this script."
        }

        Start-OllamaIfNeeded
        Invoke-Checked "ollama" @("pull", $OllamaModel)
    }

    Write-Step "Running verification checks"
    Invoke-Checked $VenvPython @("-m", "compileall", "-q", "generate_short.py", "run_pipeline.py", "upload_youtube.py", "test_voice.py")
    Invoke-Checked $VenvPython @("-m", "ruff", "check", ".")
    Invoke-Checked $VenvPython @("-m", "bandit", "-q", "-r", ".", "--severity-level", "medium", "--confidence-level", "high", "-x", "./.git,./.venv,./outputs,./voices,./assets/music")

    Write-Step "Setup complete"
    Write-Host "Activate the environment:" -ForegroundColor Green
    Write-Host "  .\.venv\Scripts\Activate.ps1"
    Write-Host ""
    Write-Host "Generate a test short:" -ForegroundColor Green
    Write-Host '  python run_pipeline.py --topic "What an ETF is in under 60 seconds"'
    Write-Host ""
    Write-Host "For YouTube upload, place client_secret.json in the project root first."
} finally {
    Pop-Location
}
