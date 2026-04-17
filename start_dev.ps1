param(
    [switch]$SkipBootstrap,
    [switch]$SkipModelPull,
    [switch]$SkipChecks,
    [switch]$DryRun,
    [string]$OllamaModel = "",
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvPath = Join-Path $Root ".env"
$SetupScript = Join-Path $Root "setup_windows.ps1"
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$StateDir = Join-Path $Root ".dev"
$StatePath = Join-Path $StateDir "services.json"
$OllamaStdoutLog = Join-Path $StateDir "ollama.stdout.log"
$OllamaStderrLog = Join-Path $StateDir "ollama.stderr.log"

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

function Read-DotEnv {
    $values = @{}
    if (-not (Test-Path $EnvPath)) {
        return $values
    }

    foreach ($line in Get-Content -LiteralPath $EnvPath) {
        $trimmed = $line.Trim()
        if ($trimmed.Length -eq 0 -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }

        $parts = $line -split "=", 2
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()

        if ($value.Length -ge 2) {
            $first = $value.Substring(0, 1)
            $last = $value.Substring($value.Length - 1, 1)
            if (($first -eq '"' -and $last -eq '"') -or ($first -eq "'" -and $last -eq "'")) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }

        if ($key -match "^[A-Za-z_][A-Za-z0-9_]*$") {
            $values[$key] = $value
        }
    }

    return $values
}

function Import-DotEnv {
    param([hashtable]$Values)

    foreach ($key in $Values.Keys) {
        [Environment]::SetEnvironmentVariable($key, [string]$Values[$key], "Process")
    }

    if ($Values.Count -gt 0) {
        Write-Ok "Loaded .env values for this script process"
    }
}

function Resolve-OllamaModel {
    param([hashtable]$DotEnvValues)

    if (-not [string]::IsNullOrWhiteSpace($OllamaModel)) {
        return $OllamaModel
    }

    if ($DotEnvValues.ContainsKey("OLLAMA_MODEL") -and -not [string]::IsNullOrWhiteSpace($DotEnvValues["OLLAMA_MODEL"])) {
        return [string]$DotEnvValues["OLLAMA_MODEL"]
    }

    if (-not [string]::IsNullOrWhiteSpace($env:OLLAMA_MODEL)) {
        return $env:OLLAMA_MODEL
    }

    return "llama3.1:8b"
}

function Get-OllamaBaseUrl {
    param([hashtable]$DotEnvValues)

    $raw = $null
    if ($DotEnvValues.ContainsKey("OLLAMA_URL")) {
        $raw = [string]$DotEnvValues["OLLAMA_URL"]
    }

    if ([string]::IsNullOrWhiteSpace($raw)) {
        $raw = $env:OLLAMA_URL
    }

    if ([string]::IsNullOrWhiteSpace($raw)) {
        return "http://localhost:11434"
    }

    if ($raw -notmatch "^https?://") {
        $raw = "http://$raw"
    }

    try {
        $uri = [Uri]$raw
        if ($uri.IsAbsoluteUri) {
            return "$($uri.Scheme)://$($uri.Authority)".TrimEnd("/")
        }
    } catch {
        Write-Warn "Could not parse OLLAMA_URL; using http://localhost:11434"
    }

    return "http://localhost:11434"
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
        Write-Warn "Could not read .dev service state; it will be replaced"
        return $null
    }
}

function Save-ServiceState {
    param([hashtable]$State)

    if ($DryRun) {
        Write-Host "DRY RUN would write $StatePath"
        return
    }

    New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
    $State | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $StatePath -Encoding UTF8
}

function Test-ProcessById {
    param([object]$ProcessId)

    if ($null -eq $ProcessId) {
        return $false
    }

    try {
        $process = Get-Process -Id ([int]$ProcessId) -ErrorAction Stop
        return $process.ProcessName -like "ollama*"
    } catch {
        return $false
    }
}

function Invoke-ProcessWithTimeout {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [int]$Seconds = 10
    )

    if ($DryRun) {
        return @{
            ExitCode = $null
            TimedOut = $false
            Stdout = ""
            Stderr = ""
        }
    }

    New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
    $id = [Guid]::NewGuid().ToString("N")
    $stdoutPath = Join-Path $StateDir "process-$id.out"
    $stderrPath = Join-Path $StateDir "process-$id.err"

    try {
        $process = Start-Process `
            -FilePath $FilePath `
            -ArgumentList $Arguments `
            -WorkingDirectory $Root `
            -NoNewWindow `
            -PassThru `
            -RedirectStandardOutput $stdoutPath `
            -RedirectStandardError $stderrPath

        if (-not $process.WaitForExit($Seconds * 1000)) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            return @{
                ExitCode = $null
                TimedOut = $true
                Stdout = if (Test-Path $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw } else { "" }
                Stderr = if (Test-Path $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw } else { "" }
            }
        }

        $process.Refresh()
        $exitCode = if ($process.HasExited) { $process.ExitCode } else { $null }

        return @{
            ExitCode = $exitCode
            TimedOut = $false
            Stdout = if (Test-Path $stdoutPath) { Get-Content -LiteralPath $stdoutPath -Raw } else { "" }
            Stderr = if (Test-Path $stderrPath) { Get-Content -LiteralPath $stderrPath -Raw } else { "" }
        }
    } finally {
        Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
    }
}

function Get-OllamaHealthBaseUrls {
    param([string]$BaseUrl)

    $urls = New-Object System.Collections.Generic.List[string]
    $urls.Add($BaseUrl.TrimEnd("/"))

    try {
        $uri = [Uri]$BaseUrl
        if ($uri.Host -eq "localhost") {
            $builder = [UriBuilder]$uri
            $builder.Host = "127.0.0.1"
            $urls.Add($builder.Uri.AbsoluteUri.TrimEnd("/"))
        }
    } catch {
        return @($urls | Select-Object -Unique)
    }

    return @($urls | Select-Object -Unique)
}

function Test-OllamaHttpServer {
    param([string]$BaseUrl)

    foreach ($healthBaseUrl in Get-OllamaHealthBaseUrls -BaseUrl $BaseUrl) {
        $tagsUrl = "$healthBaseUrl/api/tags"

        if (Test-Command "curl.exe") {
            $curl = Invoke-ProcessWithTimeout `
                -FilePath "curl.exe" `
                -Arguments @("--fail", "--silent", "--show-error", "--max-time", "5", $tagsUrl) `
                -Seconds 7
            if (-not $curl.TimedOut -and $curl.ExitCode -eq 0) {
                return $true
            }
        }

        try {
            Invoke-WebRequest -Uri $tagsUrl -UseBasicParsing -TimeoutSec 5 | Out-Null
            return $true
        } catch {
            continue
        }
    }

    return $false
}

function Test-OllamaServer {
    param([string]$BaseUrl)

    return (Test-OllamaHttpServer -BaseUrl $BaseUrl)
}

function Get-OllamaHttpModelResult {
    param([string]$BaseUrl)

    foreach ($healthBaseUrl in Get-OllamaHealthBaseUrls -BaseUrl $BaseUrl) {
        $tagsUrl = "$healthBaseUrl/api/tags"

        if (Test-Command "curl.exe") {
            $curl = Invoke-ProcessWithTimeout `
                -FilePath "curl.exe" `
                -Arguments @("--fail", "--silent", "--show-error", "--max-time", "5", $tagsUrl) `
                -Seconds 7
            if (-not $curl.TimedOut -and $curl.ExitCode -eq 0) {
                try {
                    $json = $curl.Stdout | ConvertFrom-Json
                    $models = @($json.models | ForEach-Object { [string]$_.name })
                    return [pscustomobject]@{
                        Succeeded = $true
                        Models = $models
                    }
                } catch {
                    Write-Warn "Could not parse Ollama model list from curl response"
                }
            }
        }

        try {
            $response = Invoke-WebRequest -Uri $tagsUrl -UseBasicParsing -TimeoutSec 5
            $json = $response.Content | ConvertFrom-Json
            $models = @($json.models | ForEach-Object { [string]$_.name })
            return [pscustomobject]@{
                Succeeded = $true
                Models = $models
            }
        } catch {
            continue
        }
    }

    return [pscustomobject]@{
        Succeeded = $false
        Models = @()
    }
}

function Get-OllamaProcesses {
    return @(
        Get-Process -ErrorAction SilentlyContinue |
            Where-Object { $_.ProcessName -like "ollama*" } |
            Sort-Object @{ Expression = { if ($_.ProcessName -eq "ollama app") { 0 } else { 1 } } }, ProcessName, Id
    )
}

function Stop-StaleOllamaProcesses {
    param([string]$Reason)

    $processes = @(Get-OllamaProcesses)
    if ($processes.Count -eq 0) {
        return
    }

    Write-Warn $Reason
    foreach ($process in $processes) {
        if ($DryRun) {
            Write-Host "DRY RUN would stop stale Ollama process $($process.Id) ($($process.ProcessName))"
            continue
        }

        Write-Host "Stopping stale Ollama process $($process.Id) ($($process.ProcessName))"
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }

    if (-not $DryRun) {
        Start-Sleep -Seconds 1
    }
}

function Get-LogTail {
    param(
        [string]$Path,
        [int]$Lines = 20
    )

    if (-not (Test-Path $Path)) {
        return ""
    }

    return ((Get-Content -LiteralPath $Path -Tail $Lines) -join "`n").Trim()
}

function Wait-OllamaServer {
    param(
        [string]$BaseUrl,
        [int]$Seconds,
        [object]$Process = $null
    )

    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-OllamaServer -BaseUrl $BaseUrl) {
            return
        }

        if ($null -ne $Process -and $Process.HasExited) {
            $stderrTail = Get-LogTail -Path $OllamaStderrLog
            $stdoutTail = Get-LogTail -Path $OllamaStdoutLog
            $logText = (($stderrTail, $stdoutTail) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join "`n"
            if ([string]::IsNullOrWhiteSpace($logText)) {
                $logText = "No Ollama log output was captured."
            }
            throw "Ollama exited before it became ready. Exit code: $($Process.ExitCode). Log tail:`n$logText"
        }

        Start-Sleep -Seconds 1
    }

    $stderrTail = Get-LogTail -Path $OllamaStderrLog
    $stdoutTail = Get-LogTail -Path $OllamaStdoutLog
    $logText = (($stderrTail, $stdoutTail) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }) -join "`n"
    if ([string]::IsNullOrWhiteSpace($logText)) {
        $logText = "No Ollama log output was captured."
    }
    throw "Ollama did not become ready at $BaseUrl within $Seconds seconds. Log tail:`n$logText"
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $Root
    )

    Write-Host "RUN $FilePath $($Arguments -join ' ')"
    if ($DryRun) {
        return
    }

    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -NoNewWindow -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "$FilePath exited with code $($process.ExitCode)"
    }
}

function Assert-DevBaseline {
    param([string]$Model)

    $missing = New-Object System.Collections.Generic.List[string]
    if (-not (Test-Path $VenvPython)) {
        $missing.Add(".venv Python")
    }
    if (-not (Test-Path $EnvPath)) {
        $missing.Add(".env")
    }
    if (-not (Test-Path (Join-Path $Root "config.json"))) {
        $missing.Add("config.json")
    }

    if ($missing.Count -eq 0) {
        Write-Ok "Local Python environment and config files are present"
        return
    }

    Write-Warn "Missing baseline setup: $($missing -join ', ')"
    if ($SkipBootstrap) {
        throw "Run .\setup_windows.ps1 first, or rerun this script without -SkipBootstrap."
    }

    if (-not (Test-Path $SetupScript)) {
        throw "setup_windows.ps1 is missing, so the baseline setup cannot be delegated."
    }

    Write-Step "Delegating baseline setup to setup_windows.ps1"
    $setupArgs = @("-SkipOllamaPull")
    if (-not [string]::IsNullOrWhiteSpace($Model)) {
        $setupArgs += @("-OllamaModel", $Model)
    }

    Write-Host "RUN $SetupScript $($setupArgs -join ' ')"
    if (-not $DryRun) {
        & $SetupScript @setupArgs
    }
}

function Start-OllamaServer {
    param([string]$BaseUrl)

    $state = Read-ServiceState
    $ollamaState = Get-ObjectProperty -Object $state -Name "ollama"
    $previousStarted = [bool](Get-ObjectProperty -Object $ollamaState -Name "started_by_script")
    $previousPid = Get-ObjectProperty -Object $ollamaState -Name "pid"

    if (Test-OllamaServer -BaseUrl $BaseUrl) {
        if ($previousStarted -and (Test-ProcessById -ProcessId $previousPid)) {
            Write-Ok "Ollama is already running and tracked by this project"
            return @{ StartedByScript = $true; Pid = [int]$previousPid }
        }

        Write-Ok "Ollama server is already running"
        return @{ StartedByScript = $false; Pid = $null }
    }

    if (@(Get-OllamaProcesses).Count -gt 0) {
        Stop-StaleOllamaProcesses -Reason "Ollama processes exist, but the health check failed. Restarting them."
    }

    Write-Step "Starting Ollama server"
    if ($DryRun) {
        Write-Host "DRY RUN would start: ollama serve"
        return @{ StartedByScript = $true; Pid = $null }
    }

    if (-not (Test-Command "ollama")) {
        throw "Ollama is not available in PATH. Run .\setup_windows.ps1, or install Ollama manually."
    }

    New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
    Remove-Item -LiteralPath $OllamaStdoutLog, $OllamaStderrLog -Force -ErrorAction SilentlyContinue

    $process = Start-Process `
        -FilePath "ollama" `
        -ArgumentList @("serve") `
        -WindowStyle Hidden `
        -PassThru `
        -RedirectStandardOutput $OllamaStdoutLog `
        -RedirectStandardError $OllamaStderrLog

    Wait-OllamaServer -BaseUrl $BaseUrl -Seconds $TimeoutSeconds -Process $process
    Write-Ok "Ollama server started"
    return @{ StartedByScript = $true; Pid = $process.Id }
}

function Test-OllamaModelPresent {
    param(
        [string]$BaseUrl,
        [string]$Model
    )

    $modelResult = Get-OllamaHttpModelResult -BaseUrl $BaseUrl
    if ($modelResult.Succeeded) {
        return (@($modelResult.Models) -contains $Model)
    }

    Write-Warn "Could not read Ollama model list"
    return $null
}

function Ensure-OllamaModel {
    param(
        [string]$BaseUrl,
        [string]$Model
    )

    if ($SkipModelPull) {
        Write-Warn "Skipping Ollama model pull"
        return
    }

    if ($DryRun) {
        Write-Host "DRY RUN would ensure Ollama model $Model is available"
        return
    }

    $modelPresent = Test-OllamaModelPresent -BaseUrl $BaseUrl -Model $Model
    if ($modelPresent -eq $true) {
        Write-Ok "Ollama model $Model is available"
        return
    }

    if ($null -eq $modelPresent) {
        Write-Warn "Could not verify the Ollama model list; leaving model pull to setup_windows.ps1 or manual ollama pull"
        return
    }

    if (-not (Test-Command "ollama")) {
        throw "Ollama CLI is not available in PATH."
    }

    Write-Step "Pulling Ollama model $Model"
    Invoke-Checked "ollama" @("pull", $Model)
}

function Invoke-QuickChecks {
    if ($SkipChecks) {
        Write-Warn "Skipping quick Python checks"
        return
    }

    if (-not (Test-Path $VenvPython)) {
        Write-Warn "Skipping quick Python checks because .venv is missing"
        return
    }

    Write-Step "Running quick Python syntax checks"
    Invoke-Checked $VenvPython @(
        "-m",
        "compileall",
        "-q",
        "generate_short.py",
        "run_pipeline.py",
        "setup_channel.py",
        "upload_youtube.py",
        "test_voice.py"
    )
}

Push-Location $Root
try {
    Write-Step "Finance Shorts Factory dev environment"
    Write-Host "Project root: $Root"

    $dotEnvValues = Read-DotEnv
    $resolvedModel = Resolve-OllamaModel -DotEnvValues $dotEnvValues

    Assert-DevBaseline -Model $resolvedModel

    $dotEnvValues = Read-DotEnv
    Import-DotEnv -Values $dotEnvValues
    $resolvedModel = Resolve-OllamaModel -DotEnvValues $dotEnvValues
    $ollamaBaseUrl = Get-OllamaBaseUrl -DotEnvValues $dotEnvValues

    $ollamaRuntime = Start-OllamaServer -BaseUrl $ollamaBaseUrl
    Ensure-OllamaModel -BaseUrl $ollamaBaseUrl -Model $resolvedModel

    Save-ServiceState @{
        project_root = $Root
        generated_at = (Get-Date).ToString("o")
        ollama = @{
            base_url = $ollamaBaseUrl
            model = $resolvedModel
            started_by_script = [bool]$ollamaRuntime.StartedByScript
            pid = $ollamaRuntime.Pid
        }
    }

    Invoke-QuickChecks

    Write-Step "Dev environment ready"
    Write-Host "Ollama: $ollamaBaseUrl"
    Write-Host "Model: $resolvedModel"
    Write-Host "Python: $VenvPython"
    Write-Host ""
    Write-Host "Use the project Python directly:"
    Write-Host "  .\.venv\Scripts\python.exe run_pipeline.py"
    Write-Host ""
    Write-Host "Or activate the environment in your terminal:"
    Write-Host "  .\.venv\Scripts\Activate.ps1"
    Write-Host ""
    Write-Host "Stop the local dev services:"
    Write-Host "  .\stop_dev.ps1"
} finally {
    Pop-Location
}
