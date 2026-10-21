# Vey Arc's Tutorials - one-step setup for an episode's code folder (Windows PowerShell 5.1+).
# Double-click setup.cmd (or run it from a terminal). It:
#   1. finds Python 3.13 and creates .venv (only the first time)
#   2. installs requirements.txt (only when it changed)
#   3. runs the offline tests
#   4. activates .venv, sets the provider variables, asks for the API key if none is set
#   5. opens the demo folder, ready to record:  run  (list)  /  run 1  (record run 1)
# Episode settings: setup.env (KEY=VALUE lines). Run list: runs.txt ("label | task" lines).
# The API key is never written to any file in this folder.

$ErrorActionPreference = "Continue"   # native tools (py, pip) write warnings to stderr; exit codes are checked instead
$Here = $PSScriptRoot
Set-Location $Here
function Say($msg, $color = "Cyan") { Write-Host "[setup] $msg" -ForegroundColor $color }
function Fail($msg) { Write-Host "[setup] $msg" -ForegroundColor Red; throw "setup stopped" }

try {
    # ---- 1. Python 3.13 + .venv ----
    $venvPy = Join-Path $Here ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPy)) {
        $base = $null
        try { $base = (& py -3.13 -c "import sys; print(sys.executable)" 2>$null) } catch {}
        if (-not $base) {
            Fail "Python 3.13 not found. Install it from https://www.python.org/downloads/ (tick 'py launcher'), then run setup again."
        }
        Say "creating .venv with $base"
        & py -3.13 -m venv .venv
        if ($LASTEXITCODE -ne 0) { Fail "could not create .venv" }
    }
    $ver = & $venvPy -c "import platform; print(platform.python_version())"
    Say "Python $ver (.venv)"

    # ---- 2. requirements (skip when unchanged) ----
    $req = Join-Path $Here "requirements.txt"
    $stamp = Join-Path $Here ".venv\requirements.sha256"
    $hash = (Get-FileHash $req -Algorithm SHA256).Hash
    if (-not (Test-Path $stamp) -or (Get-Content $stamp -Raw).Trim() -ne $hash) {
        Say "installing requirements.txt"
        & $venvPy -m pip install --disable-pip-version-check -q -r $req
        if ($LASTEXITCODE -ne 0) { Fail "pip install failed (see the error above)" }
        Set-Content $stamp $hash
    } else {
        Say "requirements already installed"
    }

    # ---- 3. offline tests ----
    $tests = Get-ChildItem (Join-Path $Here "tests") -Filter "test_*.py" -ErrorAction SilentlyContinue
    foreach ($t in $tests) {
        $out = & $venvPy $t.FullName 2>&1
        if ($LASTEXITCODE -ne 0) { $out | Select-Object -Last 15 | Write-Host; Fail "offline tests failed: $($t.Name)" }
        Say (($out | Select-Object -Last 1) -join "") "Green"
    }

    # ---- 4. activate + variables ----
    . (Join-Path $Here ".venv\Scripts\Activate.ps1")
    $env:PYTHONUTF8 = "1"
    if (-not $env:OPENAI_BASE_URL) { $env:OPENAI_BASE_URL = "https://api.deepseek.com" }
    if (-not $env:AGENT_MODEL)     { $env:AGENT_MODEL = "deepseek-flash" }
    $envFile = Join-Path $Here "setup.env"
    if (Test-Path $envFile) {
        foreach ($line in Get-Content $envFile) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$' -and $Matches[1] -ne "OPENAI_API_KEY") {
                Set-Item "env:$($Matches[1])" $Matches[2].Trim()
            }
        }
    }
    if (-not $env:OPENAI_API_KEY) {
        $saved = [Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "User")
        if ($saved) { $env:OPENAI_API_KEY = $saved }
    }
    if (-not $env:OPENAI_API_KEY) {
        $sec = Read-Host "[setup] API key for $($env:OPENAI_BASE_URL) (input hidden)" -AsSecureString
        $env:OPENAI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
        if ((Read-Host "[setup] remember it for future windows (your Windows user variables)? [y/N]") -eq "y") {
            [Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $env:OPENAI_API_KEY, "User")
            Say "saved as a user environment variable"
        }
    }
    Say "OPENAI_BASE_URL = $env:OPENAI_BASE_URL"
    Say "AGENT_MODEL     = $env:AGENT_MODEL"
    if ($env:AGENT_WRITABLE) { Say "AGENT_WRITABLE  = $env:AGENT_WRITABLE" }
    Say "OPENAI_API_KEY  = (set)"

    # ---- 5. run helper ----
    $global:VatRuns = @()
    $runsFile = Join-Path $Here "runs.txt"
    if (Test-Path $runsFile) {
        $global:VatRuns = @(Get-Content $runsFile | Where-Object { $_ -match '\|' -and $_ -notmatch '^\s*#' })
    }
    $global:VatRecorder = Join-Path $Here "record_run.py"
    function global:run([int]$n = 0) {
        if ($n -lt 1 -or $n -gt $global:VatRuns.Count) {
            Write-Host ""
            for ($i = 0; $i -lt $global:VatRuns.Count; $i++) {
                $label = ($global:VatRuns[$i] -split '\|', 2)[0].Trim()
                Write-Host ("  run {0}   {1}" -f ($i + 1), $label)
            }
            Write-Host ""
            return
        }
        $task = ($global:VatRuns[$n - 1] -split '\|', 2)[1].Trim()
        python $global:VatRecorder $task
    }
    $demo = Join-Path $Here "demo"
    if (Test-Path $demo) { Set-Location $demo }
    Say "ready. Type  run  to list the recording runs, run 1 to start the first." "Green"
    if ($global:VatRuns.Count) { run }
}
catch {
    if ($_.Exception.Message -ne "setup stopped") { Write-Host "[setup] $($_.Exception.Message)" -ForegroundColor Red }
}
