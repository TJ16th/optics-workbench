[CmdletBinding()]
param(
    [string]$IncomingWorkOrders = 'F:\vscode\claude\opt\doc\work_orders\active',
    [string]$CodexWorkOrders = 'F:\vscode\opt\doc\work_orders\active',
    [string]$CodexReports = 'F:\vscode\opt\doc\reports',
    [string]$ClaudeReports = 'F:\vscode\claude\opt\doc\reports',
    [string]$LogPath = (Join-Path $env:LOCALAPPDATA 'OpticsDocSync\sync.log'),
    [int]$PollMilliseconds = 750
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

foreach ($path in @($IncomingWorkOrders, $CodexWorkOrders, $CodexReports, $ClaudeReports)) {
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

$logDirectory = Split-Path -Parent $LogPath
if (-not (Test-Path -LiteralPath $logDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
}

$routes = @(
    [pscustomobject]@{ Mode = 'work_orders'; SourceRoot = $IncomingWorkOrders; DestinationRoot = $CodexWorkOrders; Recurse = $false },
    [pscustomobject]@{ Mode = 'reports'; SourceRoot = $CodexReports; DestinationRoot = $ClaudeReports; Recurse = $true }
)

function Get-RelativeSyncPath {
    param([string]$Root, [string]$Path)
    $prefix = $Root.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    if (-not $Path.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside sync root: $Path"
    }
    return $Path.Substring($prefix.Length)
}

function Get-SyncFiles {
    param([pscustomobject]$Route)
    $files = Get-ChildItem -LiteralPath $Route.SourceRoot -File -Recurse:$Route.Recurse -ErrorAction SilentlyContinue
    if ($Route.Mode -eq 'work_orders') { return $files }
    return $files | Where-Object {
        $relative = Get-RelativeSyncPath -Root $Route.SourceRoot -Path $_.FullName
        $isRootMarkdown = -not $relative.Contains([System.IO.Path]::DirectorySeparatorChar) -and $_.Extension -eq '.md'
        $isScreenshot = $relative.StartsWith("screenshots$([System.IO.Path]::DirectorySeparatorChar)", [System.StringComparison]::OrdinalIgnoreCase)
        $isRootMarkdown -or $isScreenshot
    }
}

function Get-FileSignature {
    param([System.IO.FileInfo]$File)
    return "$($File.LastWriteTimeUtc.Ticks):$($File.Length)"
}

function Test-SyncFilesEqual {
    param([System.IO.FileInfo]$Source, [string]$DestinationPath)
    if (-not (Test-Path -LiteralPath $DestinationPath -PathType Leaf)) { return $false }
    $destination = Get-Item -LiteralPath $DestinationPath
    if ($Source.Length -ne $destination.Length) { return $false }
    return (Get-FileHash -LiteralPath $Source.FullName -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $DestinationPath -Algorithm SHA256).Hash
}

function Copy-SyncFile {
    param([pscustomobject]$Route, [System.IO.FileInfo]$File)
    $relativePath = Get-RelativeSyncPath -Root $Route.SourceRoot -Path $File.FullName
    $destinationPath = Join-Path $Route.DestinationRoot $relativePath
    $destinationDirectory = Split-Path -Parent $destinationPath
    for ($attempt = 1; $attempt -le 8; $attempt++) {
        try {
            if (-not (Test-Path -LiteralPath $destinationDirectory -PathType Container)) {
                New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
            }
            Copy-Item -LiteralPath $File.FullName -Destination $destinationPath -Force
            Add-Content -LiteralPath $LogPath -Value "$(Get-Date -Format o) [$($Route.Mode)] $relativePath"
            return $true
        }
        catch {
            if ($attempt -eq 8) {
                Add-Content -LiteralPath $LogPath -Value "$(Get-Date -Format o) [error] $relativePath :: $($_.Exception.Message)"
                return $false
            }
            Start-Sleep -Milliseconds (100 * $attempt)
        }
    }
}

$known = @{}
foreach ($route in $routes) {
    $known[$route.Mode] = @{}
    foreach ($file in Get-SyncFiles -Route $route) {
        $relativePath = Get-RelativeSyncPath -Root $route.SourceRoot -Path $file.FullName
        $destinationPath = Join-Path $route.DestinationRoot $relativePath
        if (-not (Test-SyncFilesEqual -Source $file -DestinationPath $destinationPath)) {
            Copy-SyncFile -Route $route -File $file | Out-Null
        }
        $known[$route.Mode][$file.FullName] = Get-FileSignature -File $file
    }
}

Add-Content -LiteralPath $LogPath -Value "$(Get-Date -Format o) [started] polling=$PollMilliseconds"
while ($true) {
    Start-Sleep -Milliseconds $PollMilliseconds
    foreach ($route in $routes) {
        $currentPaths = @{}
        foreach ($file in Get-SyncFiles -Route $route) {
            $currentPaths[$file.FullName] = $true
            $signature = Get-FileSignature -File $file
            $previous = $known[$route.Mode][$file.FullName]
            if ($null -eq $previous -or $previous -ne $signature) {
                if (Copy-SyncFile -Route $route -File $file) {
                    $known[$route.Mode][$file.FullName] = $signature
                }
            }
        }
        foreach ($knownPath in @($known[$route.Mode].Keys)) {
            if (-not $currentPaths.ContainsKey($knownPath)) {
                $known[$route.Mode].Remove($knownPath)
            }
        }
    }
}
