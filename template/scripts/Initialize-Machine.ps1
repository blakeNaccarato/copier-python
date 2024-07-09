<#.SYNOPSIS
Finish machine initialization (cross-platform).#>

. scripts/Common.ps1
. scripts/Initialize-Shell.ps1

# Set Git username if missing
try { $name = git config --global 'user.name' }
catch [System.Management.Automation.NativeCommandExitException] { $name = '' }
if (!$name) {
    git config --global 'user.name' "$((Get-Content '.copier-answers.yml' |
    Select-String -Pattern '^project_owner_github_username:\s(.+)$').Matches.Groups[1].value)"
    # Have Git auto set up local branches to track remote branches if not yet configured
    try { $auto = git config --global 'push.autoSetupRemote' }
    catch [System.Management.Automation.NativeCommandExitException] { $auto = '' }
    if (!$auto) { git config --global 'push.autoSetupRemote' 'true' }
}

# Set Git email if missing
try { $email = git config --global 'user.email' }
catch [System.Management.Automation.NativeCommandExitException] { $email = '' }
if (!$email) {
    git config --global 'user.email' "$((Get-Content '.copier-answers.yml' |
    Select-String -Pattern '^project_email:\s(.+)$').Matches.Groups[1].value)"
}

# Log in to GitHub API
if (! (gh auth status)) {
    'LOGGING IN TO GITHUB API' | Write-Progress
    gh auth login
    'GITHUB API LOGIN COMPLETE' | Write-Progress -Done
}

# Install VSCode local workspace extensions
$Install = @(
    '--extensions-dir=.vscode/extensions',
    '--install-extension=charliermarsh.ruff@2024.30.0',
    '--install-extension=ms-python.vscode-pylance@2024.6.1'
)
code @Install
# Remove Pylance bundled stubs
Get-ChildItem -Path '.vscode/extensions' -Filter 'ms-python.vscode-pylance-*' |
    ForEach-Object {
        Get-ChildItem -Path "$($_.FullName)/dist/bundled" -Filter '*stubs'
    } |
    Remove-Item -Recurse
