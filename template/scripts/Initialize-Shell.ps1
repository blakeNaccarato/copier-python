<#
.SYNOPSIS
Initialization commands for PowerShell shells in pre-commit and tasks.#>

# ? Error-handling
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$ErrorView = 'NormalView'

# ? Fix leaky UTF-8 encoding settings on Windows
if ($IsWindows) {
    # Now PowerShell pipes will be UTF-8. Note that fixing it from Control Panel and
    # system-wide has buggy downsides.
    # See: https://github.com/PowerShell/PowerShell/issues/7233#issuecomment-640243647
    [console]::InputEncoding = [console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
}

# ? Environment setup
function Set-Env {
    <#.SYNOPSIS
    Activate virtual environment and set environment variables.#>

    # ? Set environment variables
    $LocalBin = (Test-Path 'bin') ? (Get-Item 'bin') : (New-Item -ItemType Directory 'bin')
    $Vars = $Env:GITHUB_ENV ? $(Get-Content $Env:GITHUB_ENV |
            Select-String -Pattern '^(.+)=.+$' |
            ForEach-Object { $_.Matches.Groups[1].value }) : @{}
    foreach ($i in @{
            PATH                           = "$LocalBin$($IsWindows ? ';' : ':')$Env:PATH"
            PYRIGHT_PYTHON_PYLANCE_VERSION = '2024.7.1'
            PYDEVD_DISABLE_FILE_VALIDATION = '1'
            PYTHONIOENCODING               = 'utf-8:strict'
            PYTHONWARNDEFAULTENCODING      = '1'
            PYTHONWARNINGS                 = 'ignore'
            COVERAGE_CORE                  = 'sysmon'
        }.GetEnumerator() ) {
        Set-Item "Env:$($i.Key)" $($i.Value)
        if ($Env:GITHUB_ENV -and ($i.Key -notin $Vars)) {
            "$($i.Key)=$($i.Value)" >> $Env:GITHUB_ENV
        }
    }

    # ? Activate virtual environment if one exists
    if (Test-Path '.venv') {
        if ($IsWindows) { .venv/scripts/activate.ps1 } else { .venv/bin/activate.ps1 }
    }

}
Set-Env
