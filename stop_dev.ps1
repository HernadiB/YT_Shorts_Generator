param(
    [switch]$ForceAllOllama,
    [switch]$KeepExternalOllama,
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

function Get-OllamaProcesses {
    return @(
        Get-Process -ErrorAction SilentlyContinue |
            Where-Object { $_.ProcessName -like "ollama*" } |
            Sort-Object @{ Expression = { if ($_.ProcessName -eq "ollama app") { 0 } else { 1 } } }, ProcessName, Id
    )
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

function Stop-OllamaProcess {
    param(
        [object]$ProcessId,
        [string]$Reason
    )

    $process = Get-OllamaProcess -ProcessId $ProcessId
    if ($null -eq $process) {
        return $false
    }

    Write-Step "Stopping Ollama process $($process.Id)"
    if (-not [string]::IsNullOrWhiteSpace($Reason)) {
        Write-Host $Reason
    }

    if ($DryRun) {
        Write-Host "DRY RUN would stop process $($process.Id)"
        return $true
    }

    Stop-Process -Id $process.Id -Force -ErrorAction Stop
    Wait-ProcessExit -ProcessId $process.Id -Seconds $TimeoutSeconds

    if ($null -eq (Get-OllamaProcess -ProcessId $process.Id)) {
        Write-Ok "Stopped Ollama process $($process.Id)"
    } else {
        Write-Warn "Ollama process $($process.Id) did not exit within $TimeoutSeconds seconds"
    }

    return $true
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

    $stopped = Stop-OllamaProcess -ProcessId $trackedPid -Reason "Tracked by .dev service state."
    if (-not $stopped) {
        Write-Warn "Tracked Ollama process is not running"
    }
}

function Stop-AllOllama {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $sawProcess = $false

    while ($true) {
        $processes = @(Get-OllamaProcesses)
        if ($processes.Count -eq 0) {
            if ($sawProcess) {
                Write-Ok "No Ollama processes remain"
            } else {
                Write-Ok "No Ollama processes are running"
            }
            return
        }

        $sawProcess = $true
        Write-Step "Stopping all Ollama processes"
        foreach ($process in $processes) {
            [void](Stop-OllamaProcess -ProcessId $process.Id -Reason "Local Ollama shutdown.")
        }

        if ($DryRun) {
            return
        }

        Start-Sleep -Milliseconds 500
        if ((Get-Date) -ge $deadline) {
            $remaining = @(Get-OllamaProcesses)
            if ($remaining.Count -gt 0) {
                $remainingList = ($remaining | ForEach-Object { "$($_.ProcessName)($($_.Id))" }) -join ", "
                throw "Ollama processes are still running after $TimeoutSeconds seconds: $remainingList"
            }
        }
    }
}

Push-Location $Root
try {
    Write-Step "Finance Shorts Factory dev shutdown"
    Write-Host "Project root: $Root"

    Stop-TrackedOllama

    if ($KeepExternalOllama -and -not $ForceAllOllama) {
        Write-Warn "Keeping external Ollama processes because -KeepExternalOllama was set"
    } else {
        Stop-AllOllama
    }

    if (-not $DryRun -and (Test-Path $StatePath)) {
        Remove-Item -LiteralPath $StatePath -Force
        Write-Ok "Removed .dev service state"
    }

    Write-Step "Dev services stopped"
} finally {
    Pop-Location
}
