<#
.SYNOPSIS
    One-command install: iex (iwr -UseBasicParsing https://raw.githubusercontent.com/cyeTeam/whisper-dict/master/install.ps1).Content
#>
param([switch]$SetupOnly)

$ErrorActionPreference = 'Stop'
$Repo = 'cyeTeam/whisper-dict'
$Branch = 'master'
$InstallDir = Join-Path $env:LOCALAPPDATA 'WhisperDict'
$BinDir = Join-Path $InstallDir 'bin'
$Launcher = Join-Path $BinDir 'whisper-dict.bat'
$VenvDir = Join-Path $InstallDir 'venv'
$MainPy = Join-Path $InstallDir 'main.py'
$SetupPy = Join-Path $InstallDir 'setup.py'

$Host.UI.RawUI.WindowTitle = "Installing Whisper Dict..."

function Color($c, $t) { "$([char]27)[${c}m${t}$([char]27)[0m" }

Write-Output ""

if (-not $SetupOnly) {
    Write-Output (Color 96 "+----------------------------------------------+")
    Write-Output (Color 96 "|           Whisper Dict - Installer           |")
    Write-Output (Color 96 "+----------------------------------------------+")
    Write-Output ""

    # Check Python
    $py = (Get-Command 'python' -ErrorAction SilentlyContinue) -or
           (Get-Command 'python3' -ErrorAction SilentlyContinue)
    if (-not $py) {
        Write-Output (Color 91 "[FAIL] Python 3.8+ required. Get it from python.org")
        exit 1
    }
    $v = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ([version]$v -lt [version]'3.8') {
        Write-Output (Color 91 "[FAIL] Python 3.8+ required (found $v)")
        exit 1
    }
    Write-Output (Color 92 "[OK]   Python $v")

    # Download repo
    Write-Output "  Downloading Whisper Dict from $Repo ..."
    $zipUrl = "https://github.com/$Repo/archive/refs/heads/$Branch.zip"
    $zipPath = Join-Path $env:TEMP 'whisper-dict.zip'
    try {
        Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
    } catch {
        Write-Output (Color 91 "[FAIL] Download failed: $_")
        exit 1
    }

    # Extract
    Write-Output "  Extracting to $InstallDir ..."
    if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }
    $tmp = Join-Path $env:TEMP 'whisper-dict-extract'
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    Expand-Archive -Path $zipPath -DestinationPath $tmp
    $extracted = Join-Path $tmp "whisper-dict-$Branch"
    Move-Item -Path $extracted -Destination $InstallDir
    Remove-Item -Path $tmp -Recurse -Force
    Remove-Item -Path $zipPath -Force

    # Venv + deps
    Write-Output ""
    $useVenv = Read-Host "  Create virtual environment (recommended)? [Y/n]"
    $useVenv = ($useVenv -eq '' -or $useVenv -eq 'y' -or $useVenv -eq 'yes')

    if ($useVenv) {
        Write-Output "  Creating virtual environment ..."
        python -m venv $VenvDir
        if (-not $?) {
            Write-Output (Color 91 "[FAIL] venv creation failed")
            exit 1
        }
        $pip = "$VenvDir\Scripts\pip.exe"
        Write-Output "  Installing dependencies (may take a few minutes) ..."
        & $pip install -r "$InstallDir\requirements.txt"
        if (-not $?) {
            Write-Output (Color 91 "[FAIL] pip install failed")
            exit 1
        }
    } else {
        Write-Output "  Skipping venv, using system Python."
        Write-Output "  Installing dependencies (may take a few minutes) ..."
        pip install -r "$InstallDir\requirements.txt"
        if (-not $?) {
            Write-Output (Color 91 "[FAIL] pip install failed")
            exit 1
        }
    }

    # Create launcher
    Write-Output "  Creating launcher script ..."
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
    if ($useVenv) {
        '@echo off
"%~dp0..\venv\Scripts\pythonw.exe" "%~dp0..\main.py" %*' | Out-File -FilePath $Launcher -Encoding ascii
    } else {
        '@echo off
python "%~dp0..\main.py" %*' | Out-File -FilePath $Launcher -Encoding ascii
    }

    # Add to PATH
    $userPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
    if ($userPath -notlike "*$BinDir*") {
        $newPath = "$BinDir;$userPath"
        [Environment]::SetEnvironmentVariable('PATH', $newPath, 'User')
        Write-Output (Color 92 "[OK]   Added $BinDir to user PATH")
        $env:PATH = "$BinDir;$env:PATH"
    }

    Write-Output (Color 92 "[OK]   Installation complete!")
    Write-Output ""
    Write-Output "  Type $(Color 93 "whisper-dict") to launch."
    Write-Output "  Config: $(Color 93 "$env:APPDATA\WhisperDict\config.json")"
    Write-Output ""
}

# Run setup wizard
$setupPython = "$VenvDir\Scripts\python.exe"
if (Test-Path $setupPython) {
    & $setupPython $SetupPy
} else {
    python $SetupPy
}

Write-Output ""
Write-Output (Color 92 "Done! Run 'whisper-dict' from any terminal.")
