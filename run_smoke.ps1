param([switch]$Check, [switch]$V51)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = $env:CIPHEUR_PYTHON
if (-not $taskPython) {
    $taskPython = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $taskPython) {
    $taskPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
}
if (-not (Test-Path -LiteralPath $taskPython)) {
    throw 'Python 3.10+ is required. Set CIPHEUR_PYTHON to its executable path.'
}
if ($Check) {
    & $taskPython -m unittest discover -s tests -q
    if ($LASTEXITCODE -ne 0) { throw 'Integrity checks failed.' }
}
$taskConfig = if ($V51) { 'configs/v51_smoke.json' } else { 'configs/smoke.json' }
& $taskPython -m cipheur preflight --config $taskConfig
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed.' }
& $taskPython -m cipheur run --config $taskConfig
if ($LASTEXITCODE -ne 0) { throw 'Run failed.' }
