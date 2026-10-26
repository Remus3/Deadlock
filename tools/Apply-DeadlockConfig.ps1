# Apply-DeadlockConfig.ps1 - re-apply the VW repo's Deadlock configuration.
#
# Windows PowerShell 5.1. ASCII + LF. Parse-checked by tests/test_ps_parse.py;
# never executed on the dev box to test it (it reconfigures the machine).
#
# What it does, one step at a time, each backed up first and read back:
#   1. copy config/autoexec.cfg -> <Deadlock>/game/citadel/cfg/autoexec.cfg
#   2. HKCU DirectX UserGpuPreferences: deadlock.exe = GpuPreference=2;
#   3. HKCU AppCompatFlags Layers: deadlock.exe += DISABLEDXMAXIMIZEDWINDOWEDMODE
#   4. Steam launch options (tools/vw_launch.py apply) - ONLY when Steam is
#      not running; otherwise printed for a later run.
# Refuses everything while deadlock.exe runs. Backups: ops/runtime/backup/<stamp>/.
# Rollback: docs/optimization.md section "Rollback".
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\Apply-DeadlockConfig.ps1 [-WhatIf] [-SkipRegistry] [-SkipLaunchOptions]

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$SkipRegistry,
    [switch]$SkipLaunchOptions
)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$Backup = Join-Path $Repo ("ops\runtime\backup\" + $Stamp)
$GpuKey = 'HKCU:\Software\Microsoft\DirectX\UserGpuPreferences'
$LayersKey = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers'
$FsoFlag = 'DISABLEDXMAXIMIZEDWINDOWEDMODE'

function Say([string]$m) { Write-Output ('[VW] ' + $m) }

function Get-SteamRoot {
    $p = (Get-ItemProperty -Path 'HKCU:\Software\Valve\Steam' -Name SteamPath -ErrorAction SilentlyContinue).SteamPath
    if (-not $p) {
        $p = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam' -Name InstallPath -ErrorAction SilentlyContinue).InstallPath
    }
    if (-not $p) { throw 'Steam not found in the registry' }
    return ($p -replace '/', '\')
}

function Get-DeadlockDir([string]$steam) {
    $libs = @($steam)
    $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
    if (Test-Path -LiteralPath $vdf) {
        foreach ($line in Get-Content -LiteralPath $vdf) {
            if ($line -match '^\s*"path"\s*"([^"]+)"\s*$') { $libs += ($Matches[1] -replace '\\\\', '\') }
        }
    }
    foreach ($lib in $libs) {
        if (Test-Path -LiteralPath (Join-Path $lib 'steamapps\appmanifest_1422450.acf')) {
            return (Join-Path $lib 'steamapps\common\Deadlock')
        }
    }
    throw 'Deadlock (app 1422450) not found in any Steam library'
}

function Ensure-Backup {
    if (-not (Test-Path -LiteralPath $Backup)) { New-Item -ItemType Directory -Path $Backup -Force | Out-Null }
}

if (Get-Process -Name 'deadlock' -ErrorAction SilentlyContinue) {
    Say 'refused: deadlock.exe is running; close the game and re-run'
    exit 4
}

$steam = Get-SteamRoot
$game = Get-DeadlockDir $steam
$exe = Join-Path $game 'game\bin\win64\deadlock.exe'
$cfgDir = Join-Path $game 'game\citadel\cfg'
if (-not (Test-Path -LiteralPath $exe)) { throw 'deadlock.exe not found under the install' }
Say 'install found'

# 1. autoexec.cfg
$src = Join-Path $Repo 'config\autoexec.cfg'
$dst = Join-Path $cfgDir 'autoexec.cfg'
if (Test-Path -LiteralPath $dst) {
    Ensure-Backup
    Copy-Item -LiteralPath $dst -Destination (Join-Path $Backup 'autoexec.cfg') -Force
}
if ($PSCmdlet.ShouldProcess('autoexec.cfg', 'copy from repo')) {
    Copy-Item -LiteralPath $src -Destination $dst -Force
    $a = (Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash
    $b = (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash
    if ($a -ne $b) { throw 'autoexec.cfg read-back hash mismatch' }
    Say ('autoexec.cfg applied, sha256 ' + $b.Substring(0, 12))
}

if (-not $SkipRegistry) {
    Ensure-Backup
    & reg.exe export 'HKCU\Software\Microsoft\DirectX\UserGpuPreferences' (Join-Path $Backup 'UserGpuPreferences.reg') /y 2>$null | Out-Null
    & reg.exe export 'HKCU\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers' (Join-Path $Backup 'Layers.reg') /y 2>$null | Out-Null

    # 2. GPU preference: high performance
    if ($PSCmdlet.ShouldProcess($exe, 'GpuPreference=2')) {
        if (-not (Test-Path $GpuKey)) { New-Item -Path $GpuKey -Force | Out-Null }
        New-ItemProperty -Path $GpuKey -Name $exe -Value 'GpuPreference=2;' -PropertyType String -Force | Out-Null
        $rb = (Get-ItemProperty -Path $GpuKey -Name $exe).$exe
        if ($rb -ne 'GpuPreference=2;') { throw 'GPU preference read-back mismatch' }
        Say ('GPU preference read back: ' + $rb)
    }

    # 3. fullscreen optimizations off (keeps any flag already there)
    if ($PSCmdlet.ShouldProcess($exe, $FsoFlag)) {
        if (-not (Test-Path $LayersKey)) { New-Item -Path $LayersKey -Force | Out-Null }
        $cur = (Get-ItemProperty -Path $LayersKey -Name $exe -ErrorAction SilentlyContinue).$exe
        $tokens = @()
        if ($cur) { $tokens = @($cur.Split(' ') | Where-Object { $_ -and $_ -ne '~' }) }
        if ($tokens -notcontains $FsoFlag) { $tokens += $FsoFlag }
        $val = '~ ' + ($tokens -join ' ')
        New-ItemProperty -Path $LayersKey -Name $exe -Value $val -PropertyType String -Force | Out-Null
        $rb = (Get-ItemProperty -Path $LayersKey -Name $exe).$exe
        if ($rb -ne $val) { throw 'compatibility flag read-back mismatch' }
        Say ('compatibility flags read back: ' + $rb)
    }
}

# 4. Steam launch options
if (-not $SkipLaunchOptions) {
    $opts = (Get-Content -LiteralPath (Join-Path $Repo 'config\launch_options.txt') -TotalCount 1).Trim()
    if (Get-Process -Name 'steam' -ErrorAction SilentlyContinue) {
        Say ('Steam is running: launch options NOT written (Steam rewrites localconfig.vdf on exit).')
        Say ('Set them in Steam > Deadlock > Properties > Launch Options: ' + $opts)
    } elseif ($PSCmdlet.ShouldProcess('localconfig.vdf', 'LaunchOptions')) {
        & python (Join-Path $Repo 'tools\vw_launch.py') apply
        if ($LASTEXITCODE -ne 0) { throw ('vw_launch.py apply failed: ' + $LASTEXITCODE) }
    }
}

Say 'done'
exit 0
