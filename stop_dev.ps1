param(
    [switch]$ForceAllOllama,
    [switch]$DryRun,
    [int]$TimeoutSeconds = 15
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$StateDir = Join-Path $Root ".dev"
$StatePath = Join-Path $StateDir "services.json"

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

function Get-ObjectProperty {
    param(
        [object]$Object,
        [string]$Name
    )

    if ($null -eq $Object) {
        return $null
    }

    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $null
    }

    return $property.Value
}

function Read-ServiceState {
    if (-not (Test-Path $StatePath)) {
        return $null
    }

    try {
        return Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
    } catch {
        Write-Warn "Could not read .dev service state"
        return $null
    }
}

function Get-OllamaProcess {
    param([object]$ProcessId)

    if ($null -eq $ProcessId) {
        return $null
    }

    try {
        $process = Get-Process -Id ([int]$ProcessId) -ErrorAction Stop
        if ($process.ProcessName -like "ollama*") {
            return $process
        }
    } catch {
        return $null
    }

    return $null
}

function Wait-ProcessExit {
    param(
        [int]$ProcessId,
        [int]$Seconds
    )

    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if ($null -eq (Get-OllamaProcess -ProcessId $ProcessId)) {
            return
        }
        Start-Sleep -Milliseconds 250
    }
}

function Stop-TrackedOllama {
    $state = Read-ServiceState
    $ollamaState = Get-ObjectProperty -Object $state -Name "ollama"
    $startedByScript = [bool](Get-ObjectProperty -Object $ollamaState -Name "started_by_script")
    $trackedPid = Get-ObjectProperty -Object $ollamaState -Name "pid"

    if (-not $startedByScript) {
        Write-Ok "No Ollama process tracked as started by this project"
        return
    }

    $process = Get-OllamaProcess -ProcessId $trackedPid
    if ($null -eq $process) {
        Write-Warn "Tracked Ollama process is not running"
        return
    }

    Write-Step "Stopping tracked Ollama process $($process.Id)"
    if ($DryRun) {
        Write-Host "DRY RUN would stop process $($process.Id)"
        return
    }

    Stop-Process -Id $process.Id -Force -ErrorAction Stop
    Wait-ProcessExit -ProcessId $process.Id -Seconds $TimeoutSeconds
    Write-Ok "Stopped tracked Ollama process"
}

function Stop-AllOllama {
    $processes = @(Get-Process -Name "ollama" -ErrorAction SilentlyContinue)
    if ($processes.Count -eq 0) {
        Write-Ok "No Ollama processes are running"
        return
    }

    Write-Step "Stopping all Ollama processes"
    foreach ($process in $processes) {
        if ($DryRun) {
            Write-Host "DRY RUN would stop process $($process.Id)"
            continue
        }

        Stop-Process -Id $process.Id -Force -ErrorAction Stop
        Write-Ok "Stopped Ollama process $($process.Id)"
    }
}

Push-Location $Root
try {
    Write-Step "Finance Shorts Factory dev shutdown"
    Write-Host "Project root: $Root"

    Stop-TrackedOllama

    if ($ForceAllOllama) {
        Stop-AllOllama
    } elseif (-not (Test-Path $StatePath)) {
        Write-Warn "No .dev state file was found; external Ollama processes were left alone"
    }

    if (-not $DryRun -and (Test-Path $StatePath)) {
        Remove-Item -LiteralPath $StatePath -Force
        Write-Ok "Removed .dev service state"
    }

    Write-Step "Dev services stopped"
} finally {
    Pop-Location
}
