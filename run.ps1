# PowerShell 7+ recommended; Windows PowerShell 5.1 also supported.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = $PSScriptRoot
Set-Location -LiteralPath $root

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed (exit $LASTEXITCODE): $Program $($Arguments -join ' ')"
    }
}

function Assert-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required executable not found on PATH: $Name"
    }
}

try {
    Assert-Command 'latexmk'
    Assert-Command 'xelatex'
    Assert-Command 'kpsewhich'
    foreach ($font in @('pzdr.tfm', 'FandolSong-Regular.otf')) {
        $found = & kpsewhich $font
        if ($LASTEXITCODE -ne 0 -or -not $found) {
            throw "Missing TeX font $font. Install XeLaTeX, ctex/Fandol and recommended TeX fonts."
        }
    }

    $venvPython = Join-Path $root '.venv/Scripts/python.exe'
    if (-not (Test-Path (Join-Path $root '.venv/pyvenv.cfg'))) {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            Invoke-Checked 'py' @('-3.13', '-m', 'venv', '.venv')
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            Invoke-Checked 'python' @('-m', 'venv', '.venv')
        } else {
            throw 'Install Python 3.13+ and add it to PATH (or install the Windows py launcher).'
        }
    }
    if (-not (Test-Path $venvPython)) {
        throw 'Invalid .venv; remove or repair it manually.'
    }
    Invoke-Checked $venvPython @('-c', 'import sys; assert sys.version_info >= (3,13), "Python 3.13+ required"')
    $env:MPLBACKEND = 'Agg'
    $env:OPENBLAS_NUM_THREADS = '1'
    $env:OMP_NUM_THREADS = '1'

    Write-Host '[1/7] Install development dependencies'
    Invoke-Checked $venvPython @('-m','pip','install','-r','requirements-dev.txt')
    Write-Host '[2/7] Source-only repository policy'
    if (Get-Command git -ErrorAction SilentlyContinue) {
        & git rev-parse --is-inside-work-tree 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Invoke-Checked $venvPython @('scripts/check_repository.py')
        } else {
            Write-Host 'Not a Git checkout; repository policy check skipped.'
        }
    } else {
        Write-Host 'Git unavailable; repository policy check skipped.'
    }
    Write-Host '[3/7] Compile Python sources'
    Invoke-Checked $venvPython @('-m','compileall','-q','realmotion','scripts','tests')
    Write-Host '[4/7] Run tests'
    Invoke-Checked $venvPython @('-m','pytest','-q')
    Write-Host '[5/7] Smoke experiments'
    Invoke-Checked $venvPython @('-m','realmotion','--config','configs/smoke.toml')
    Write-Host '[6/7] Full experiments'
    Invoke-Checked $venvPython @('-m','realmotion','--config','configs/default.toml')
    Write-Host '[7/7] Compile and verify Chinese LaTeX'
    Invoke-Checked 'latexmk' @('-xelatex','-interaction=nonstopmode','-halt-on-error','-file-line-error','theory.tex')
    Invoke-Checked $venvPython @('scripts/check_latex_log.py','build/theory.log')
    Write-Host 'Done. PDF: build/theory.pdf ; experiments: outputs/'
} catch {
    Write-Error $_
    exit 1
}
