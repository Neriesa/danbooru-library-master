# Creates three desktop shortcuts for the built program / Создаёт на рабочем столе три ярлыка.
# Использование: make_shortcuts.ps1 -Exe "путь\к\DanbooruLibraryMaster.exe"
param([string]$Exe = "")
$ErrorActionPreference = "Stop"
if (-not $Exe) { $Exe = Join-Path $PSScriptRoot "dist\DanbooruLibraryMaster\DanbooruLibraryMaster.exe" }
if (-not (Test-Path $Exe)) { Write-Host "Program not found: $Exe"; exit 1 }
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell

function New-AppLink([string]$name, [string]$arguments) {
    $link = $shell.CreateShortcut((Join-Path $desktop ($name + ".lnk")))
    $link.TargetPath = $Exe
    $link.Arguments = $arguments
    $link.WorkingDirectory = Split-Path $Exe
    $link.IconLocation = "$Exe,0"
    $link.Save()
}

# Названия ярлыков на языке системы / shortcut names in the system language
$ru = (Get-UICulture).TwoLetterISOLanguageName -eq "ru"
if ($ru) {
    $viewerName = "Случайный просмотр"
    $browseName = "Обзор постов"
} else {
    $viewerName = "Random viewer"
    $browseName = "Post browser"
}
New-AppLink "Danbooru Library" ""
New-AppLink $viewerName "--viewer"
New-AppLink $browseName "--browse"
Write-Host "Shortcuts created on the desktop."
