Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $root

Write-Host "[tests] repo: $root"

$env:PRE_COMMIT_HOME = if ($env:PRE_COMMIT_HOME) { $env:PRE_COMMIT_HOME } else { "$root\.tmp\pre-commit-win" }
$env:BLACK_CACHE_DIR = if ($env:BLACK_CACHE_DIR) { $env:BLACK_CACHE_DIR } else { "$root\.tmp\black-cache" }
New-Item -ItemType Directory -Force $env:PRE_COMMIT_HOME | Out-Null
New-Item -ItemType Directory -Force $env:BLACK_CACHE_DIR | Out-Null

function Require-Cmd($cmd) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
    throw "[tests] ERROR: missing command: $cmd"
  }
}

function Invoke-Checked {
  param(
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)][scriptblock]$Command
  )
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "[tests] ERROR: $Label failed with exit code $LASTEXITCODE"
  }
}

function Test-PortBindable {
  param([Parameter(Mandatory = $true)][int]$Port)
  $listener = $null
  try {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    $listener.Start()
    return $true
  }
  catch {
    return $false
  }
  finally {
    if ($listener -ne $null) {
      try {
        $listener.Stop()
      }
      catch {
      }
    }
  }
}

function Resolve-E2EPort {
  param([int[]]$CandidatePorts)
  foreach ($candidate in $CandidatePorts) {
    if (Test-PortBindable -Port $candidate) {
      return $candidate
    }
  }
  throw "[tests] ERROR: could not find a bindable localhost port for Playwright E2E."
}

function Get-GitDiffSnapshot {
  param([switch]$Cached)
  if ($Cached) {
    return (& git diff --cached --binary -- . | Out-String)
  }
  return (& git diff --binary -- . | Out-String)
}

function Assert-PreCommitDidNotMutateRepo {
  param(
    [AllowEmptyString()][string]$BeforeWorktree = "",
    [AllowEmptyString()][string]$BeforeIndex = ""
  )
  $afterWorktree = Get-GitDiffSnapshot
  $afterIndex = Get-GitDiffSnapshot -Cached
  if ($BeforeWorktree -ne $afterWorktree -or $BeforeIndex -ne $afterIndex) {
    throw "[tests] ERROR: pre-commit hooks modified tracked files (worktree or index). Review/stage the hook changes, then rerun.`n$(& git status --short | Out-String)"
  }
}

Require-Cmd git
Require-Cmd node
Require-Cmd npm

$venvPython = Join-Path $root ".venv\Scripts\python.exe"

function New-ProjectVenv {
  Write-Host "[tests] Creating project venv at $root\.venv ..."
  if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -m venv .venv
  }
  elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m venv .venv
  }
  else {
    throw "[tests] ERROR: no bootstrap Python found (need py or python)"
  }
}

function Test-VenvPython {
  param([string]$PythonExe)
  if (-not (Test-Path $PythonExe)) {
    return $false
  }
  try {
    & $PythonExe -c "import sys; print(sys.executable)" | Out-Null
    return $true
  }
  catch {
    return $false
  }
}

if (-not (Test-VenvPython -PythonExe $venvPython)) {
  if (Test-Path ".venv") {
    Write-Host "[tests] WARN: existing .venv invalid; recreating ..."
    Remove-Item -Recurse -Force ".venv"
  }
  New-ProjectVenv
}

if (-not (Test-VenvPython -PythonExe $venvPython)) {
  throw "[tests] ERROR: project venv python is not runnable: $venvPython"
}

& $venvPython -m pre_commit --version | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host "[tests] Installing pre-commit into project venv ..."
  Invoke-Checked "pip install pre-commit" { & $venvPython -m pip install -U pip pre-commit }
}

& $venvPython -c "import numpy, PIL, aiohttp" | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host "[tests] Installing numpy/pillow/aiohttp into project venv ..."
  Invoke-Checked "pip install numpy pillow aiohttp" { & $venvPython -m pip install numpy pillow aiohttp }
}

$nodeMajor = [int]((& node -p "process.versions.node.split('.')[0]").Trim())
if ($nodeMajor -lt 18) {
  throw "[tests] ERROR: Node >=18 required, current=$(node -v)"
}

if (-not (Test-Path (Join-Path $root "node_modules\@playwright\test\package.json"))) {
  Write-Host "[tests] Installing frontend dependencies via npm install ..."
  Invoke-Checked "npm install" { npm install }
}

$env:ROOKIEUI_E2E_PYTHON = $venvPython
if (-not $env:ROOKIEUI_E2E_PORT) {
  $env:ROOKIEUI_E2E_PORT = [string](Resolve-E2EPort -CandidatePorts @(4173, 4300, 4310, 4320, 4500))
}
Write-Host "[tests] Playwright harness python: $env:ROOKIEUI_E2E_PYTHON"
Write-Host "[tests] Playwright harness port: $env:ROOKIEUI_E2E_PORT"

Write-Host "[tests] 1/4 detect-secrets"
Invoke-Checked "detect-secrets" { & $venvPython -m pre_commit run detect-secrets --all-files }

Write-Host "[tests] 2/4 pre-commit all hooks"
$worktreeBefore = Get-GitDiffSnapshot
$indexBefore = Get-GitDiffSnapshot -Cached
& $venvPython -m pre_commit run --all-files --show-diff-on-failure
if ($LASTEXITCODE -ne 0) {
  Write-Host "[tests] INFO: pre-commit returned non-zero; running second pass for verification ..."
  Invoke-Checked "pre-commit verify pass" { & $venvPython -m pre_commit run --all-files --show-diff-on-failure }
}
Assert-PreCommitDidNotMutateRepo -BeforeWorktree $worktreeBefore -BeforeIndex $indexBefore

Write-Host "[tests] 3/4 backend unit tests"
$env:MOLTBOT_STATE_DIR = "$root\moltbot_state\_local_unit"
Invoke-Checked "unit tests" { & $venvPython scripts\run_unittests.py --start-dir tests --pattern "test_*.py" }

Write-Host "[tests] 4/5 frontend type validation + test suite"
Invoke-Checked "npm run test:types" { npm run test:types }
Invoke-Checked "npm test" { npm test }

if ($env:ROOKIEUI_RUN_LIVE_SMOKE -eq "1") {
  Write-Host "[tests] 5/5 optional host-embedded E2E lane"
  Invoke-Checked "host-embedded E2E" { & $venvPython scripts\run_host_embedded_e2e.py }
}
else {
  Write-Host "[tests] 5/5 optional host-embedded E2E lane skipped (set ROOKIEUI_RUN_LIVE_SMOKE=1 to enable)"
}

Write-Host "[tests] PASS: full test gate completed."
