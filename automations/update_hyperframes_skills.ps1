[CmdletBinding()]
param(
    [ValidateRange(1, 24)]
    [int]$Workers = 12,
    [string]$WorkRoot = 'D:\hyperframes\skills-update',
    [string]$RepoRoot = 'D:\ai projects\vaios'
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'Continue'

$SkillNames = @(
    'hyperframes',
    'hyperframes-animation',
    'hyperframes-audio',
    'hyperframes-cli',
    'hyperframes-core',
    'hyperframes-creative',
    'hyperframes-keyframes',
    'hyperframes-registry',
    'media-use'
)

$TreeUrl = 'https://api.github.com/repos/heygen-com/hyperframes/git/trees/main?recursive=1'
$RawRoot = 'https://raw.githubusercontent.com/heygen-com/hyperframes/main'
$SelectedRoot = Join-Path $WorkRoot 'selected'
$TreeFile = Join-Path $WorkRoot 'main-tree.json'
$TreePart = "$TreeFile.part"
$LogRoot = Join-Path $WorkRoot 'curl-logs'
$TargetRoots = @(
    (Join-Path $RepoRoot '.agents\skills'),
    (Join-Path $RepoRoot '.claude\skills')
)

function Get-FullNormalizedPath {
    param([Parameter(Mandatory)][string]$Path)
    return [System.IO.Path]::GetFullPath($Path).TrimEnd('\')
}

function Assert-StrictChildPath {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Root
    )

    $fullPath = Get-FullNormalizedPath $Path
    $fullRoot = Get-FullNormalizedPath $Root
    if (-not $fullPath.StartsWith($fullRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to modify path outside the expected root: $fullPath (root: $fullRoot)"
    }
    return $fullPath
}

function Get-ValidTreeManifest {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }

    try {
        $manifest = Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
        if ($manifest.truncated -eq $true -or -not $manifest.tree) {
            return $null
        }
        return $manifest
    }
    catch {
        return $null
    }
}

function Format-BytesMb {
    param([long]$Bytes)
    return ('{0:N2}' -f ($Bytes / 1MB))
}

function Get-GitBlobSha1 {
    param([Parameter(Mandatory)][string]$Path)

    $content = [System.IO.File]::ReadAllBytes($Path)
    $header = [System.Text.Encoding]::UTF8.GetBytes("blob $($content.Length)`0")
    $combined = New-Object byte[] ($header.Length + $content.Length)
    [System.Buffer]::BlockCopy($header, 0, $combined, 0, $header.Length)
    [System.Buffer]::BlockCopy($content, 0, $combined, $header.Length, $content.Length)
    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    try {
        return (($sha1.ComputeHash($combined) | ForEach-Object { $_.ToString('x2') }) -join '')
    }
    finally {
        $sha1.Dispose()
    }
}

function Write-CombinedProgress {
    param(
        [long]$ObservedBytes,
        [long]$TotalBytes,
        [int]$CompletedFiles,
        [int]$TotalFiles,
        [long]$InitialBytes,
        [System.Diagnostics.Stopwatch]$Stopwatch
    )

    $boundedBytes = [Math]::Min($ObservedBytes, $TotalBytes)
    $percent = if ($TotalBytes -gt 0) {
        [Math]::Min(100, [Math]::Floor(($boundedBytes * 100.0) / $TotalBytes))
    }
    else { 100 }

    $elapsedSeconds = [Math]::Max($Stopwatch.Elapsed.TotalSeconds, 0.001)
    $newBytes = [Math]::Max(0, $boundedBytes - $InitialBytes)
    $bytesPerSecond = $newBytes / $elapsedSeconds
    $speedMb = $bytesPerSecond / 1MB
    $remainingBytes = [Math]::Max(0, $TotalBytes - $boundedBytes)
    $eta = if ($bytesPerSecond -gt 0) {
        [TimeSpan]::FromSeconds($remainingBytes / $bytesPerSecond).ToString('hh\:mm\:ss')
    }
    else { '--:--:--' }

    $status = ('{0}% | {1}/{2} files | {3}/{4} MB | {5:N2} MB/s | ETA {6}' -f `
        $percent,
        $CompletedFiles,
        $TotalFiles,
        (Format-BytesMb $boundedBytes),
        (Format-BytesMb $TotalBytes),
        $speedMb,
        $eta)

    Write-Progress -Id 1 -Activity 'Updating nine official HyperFrames skills' -Status $status -PercentComplete $percent
    $host.UI.RawUI.WindowTitle = "HyperFrames skills - $status"
}

function Start-FileDownload {
    param(
        [Parameter(Mandatory)]$Item,
        [Parameter(Mandatory)][string]$ErrorLog
    )

    $arguments = @(
        '--silent',
        '--show-error',
        '--location',
        '--fail',
        '--retry', '30',
        '--retry-delay', '2',
        '--retry-all-errors',
        '--connect-timeout', '30',
        '--continue-at', '-',
        '--output', $Item.PartPath,
        $Item.Url
    )

    return Start-Process -FilePath 'curl.exe' -ArgumentList $arguments -PassThru -NoNewWindow -RedirectStandardError $ErrorLog
}

foreach ($directory in @($WorkRoot, $SelectedRoot, $LogRoot) + $TargetRoots) {
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
}

$manifest = Get-ValidTreeManifest -Path $TreeFile
if (-not $manifest) {
    Write-Host 'Fetching the official GitHub file manifest...'
    if (Test-Path -LiteralPath $TreePart) {
        Remove-Item -LiteralPath (Assert-StrictChildPath -Path $TreePart -Root $WorkRoot) -Force
    }

    & curl.exe --location --fail --retry 30 --retry-delay 2 --retry-all-errors --connect-timeout 30 --output $TreePart $TreeUrl
    if ($LASTEXITCODE -ne 0) {
        throw "Could not download the GitHub tree manifest (curl exit $LASTEXITCODE)."
    }

    $downloadedManifest = Get-ValidTreeManifest -Path $TreePart
    if (-not $downloadedManifest) {
        throw 'The downloaded GitHub tree manifest is invalid or truncated.'
    }
    Move-Item -LiteralPath $TreePart -Destination $TreeFile -Force
    $manifest = $downloadedManifest
}

$prefixes = @{}
foreach ($skill in $SkillNames) {
    $prefixes["skills/$skill/"] = $skill
}

$files = New-Object System.Collections.Generic.List[object]
foreach ($blob in $manifest.tree) {
    if ($blob.type -ne 'blob') { continue }

    $matchedSkill = $null
    foreach ($prefix in $prefixes.Keys) {
        if ($blob.path.StartsWith($prefix, [System.StringComparison]::Ordinal)) {
            $matchedSkill = $prefixes[$prefix]
            break
        }
    }
    if (-not $matchedSkill) { continue }

    $relativePath = $blob.path.Substring(('skills/' + $matchedSkill + '/').Length)
    if ([string]::IsNullOrWhiteSpace($relativePath)) { continue }

    $destination = Join-Path (Join-Path $SelectedRoot $matchedSkill) ($relativePath -replace '/', '\')
    $destination = Assert-StrictChildPath -Path $destination -Root $SelectedRoot
    $partPath = "$destination.part"
    $files.Add([pscustomobject]@{
        Skill = $matchedSkill
        RepoPath = [string]$blob.path
        RelativePath = $relativePath
        Size = [long]$blob.size
        Sha = [string]$blob.sha
        Destination = $destination
        PartPath = $partPath
        Url = "$RawRoot/$($blob.path)"
        Attempts = 0
    })
}

if ($files.Count -eq 0) {
    throw 'The GitHub manifest contained none of the nine requested skill trees.'
}

foreach ($skill in $SkillNames) {
    if (-not ($files | Where-Object Skill -eq $skill | Select-Object -First 1)) {
        throw "The official GitHub tree does not contain skills/$skill/."
    }
}

$totalBytes = [long](($files | Measure-Object -Property Size -Sum).Sum)
$completedFiles = 0
$initialBytes = 0L
$pending = New-Object System.Collections.Generic.Queue[object]

foreach ($item in $files) {
    $parent = Split-Path -Parent $item.Destination
    New-Item -ItemType Directory -Path $parent -Force | Out-Null

    if ((Test-Path -LiteralPath $item.Destination -PathType Leaf) -and
        ((Get-Item -LiteralPath $item.Destination).Length -eq $item.Size) -and
        ((Get-GitBlobSha1 -Path $item.Destination) -eq $item.Sha)) {
        $completedFiles++
        $initialBytes += $item.Size
        if (Test-Path -LiteralPath $item.PartPath) {
            Remove-Item -LiteralPath (Assert-StrictChildPath -Path $item.PartPath -Root $SelectedRoot) -Force
        }
        continue
    }

    if ((Test-Path -LiteralPath $item.PartPath -PathType Leaf) -and
        ((Get-Item -LiteralPath $item.PartPath).Length -eq $item.Size) -and
        ((Get-GitBlobSha1 -Path $item.PartPath) -eq $item.Sha)) {
        Move-Item -LiteralPath $item.PartPath -Destination $item.Destination -Force
        $completedFiles++
        $initialBytes += $item.Size
        continue
    }

    if (Test-Path -LiteralPath $item.Destination) {
        Remove-Item -LiteralPath (Assert-StrictChildPath -Path $item.Destination -Root $SelectedRoot) -Force
    }
    if ((Test-Path -LiteralPath $item.PartPath) -and ((Get-Item -LiteralPath $item.PartPath).Length -gt $item.Size)) {
        Remove-Item -LiteralPath (Assert-StrictChildPath -Path $item.PartPath -Root $SelectedRoot) -Force
    }
    if (Test-Path -LiteralPath $item.PartPath) {
        $initialBytes += (Get-Item -LiteralPath $item.PartPath).Length
    }
    $pending.Enqueue($item)
}

$active = New-Object System.Collections.Generic.List[object]
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
Write-Host ("Downloading {0} official files ({1} MB) with {2} connections. Existing valid/resumable data: {3} MB." -f `
    $files.Count, (Format-BytesMb $totalBytes), $Workers, (Format-BytesMb $initialBytes))

while ($pending.Count -gt 0 -or $active.Count -gt 0) {
    while ($pending.Count -gt 0 -and $active.Count -lt $Workers) {
        $item = $pending.Dequeue()
        $item.Attempts++
        $logName = (($item.RepoPath -replace '[^A-Za-z0-9_.-]', '_') + ".attempt-$($item.Attempts).log")
        $errorLog = Join-Path $LogRoot $logName
        $process = Start-FileDownload -Item $item -ErrorLog $errorLog
        $active.Add([pscustomobject]@{ Item = $item; Process = $process; ErrorLog = $errorLog }) | Out-Null
    }

    Start-Sleep -Milliseconds 250

    for ($index = $active.Count - 1; $index -ge 0; $index--) {
        $job = $active[$index]
        $item = $job.Item
        if (-not $job.Process.HasExited) {
            # A dropped connection can leave curl retrying after the complete body is already on disk.
            # Give the file time to flush, then stop only that exact curl and validate the Git blob hash.
            if (-not (Test-Path -LiteralPath $item.PartPath -PathType Leaf)) { continue }
            $partInfo = Get-Item -LiteralPath $item.PartPath
            if ($partInfo.Length -ne $item.Size -or $partInfo.LastWriteTime -gt (Get-Date).AddMilliseconds(-750)) { continue }
            Stop-Process -Id $job.Process.Id -Force -ErrorAction SilentlyContinue
        }

        $job.Process.WaitForExit()
        $partLength = if (Test-Path -LiteralPath $item.PartPath) { (Get-Item -LiteralPath $item.PartPath).Length } else { 0L }
        $hashMatches = $partLength -eq $item.Size -and (Get-GitBlobSha1 -Path $item.PartPath) -eq $item.Sha
        if ($hashMatches) {
            Move-Item -LiteralPath $item.PartPath -Destination $item.Destination -Force
            $completedFiles++
        }
        elseif ($item.Attempts -lt 12) {
            if ($partLength -eq $item.Size -and (Test-Path -LiteralPath $item.PartPath)) {
                Remove-Item -LiteralPath (Assert-StrictChildPath -Path $item.PartPath -Root $SelectedRoot) -Force
            }
            Write-Warning "Retrying $($item.RepoPath) (attempt $($item.Attempts + 1)/12, curl exit $($job.Process.ExitCode), $partLength/$($item.Size) bytes)."
            $pending.Enqueue($item)
        }
        else {
            $details = if (Test-Path -LiteralPath $job.ErrorLog) { Get-Content -Raw -LiteralPath $job.ErrorLog } else { '' }
            throw "Download failed after 12 attempts: $($item.RepoPath). curl exit $($job.Process.ExitCode). $details"
        }
        $active.RemoveAt($index)
    }

    $observedBytes = 0L
    foreach ($item in $files) {
        if (Test-Path -LiteralPath $item.Destination -PathType Leaf) {
            $observedBytes += [Math]::Min((Get-Item -LiteralPath $item.Destination).Length, $item.Size)
        }
        elseif (Test-Path -LiteralPath $item.PartPath -PathType Leaf) {
            $observedBytes += [Math]::Min((Get-Item -LiteralPath $item.PartPath).Length, $item.Size)
        }
    }
    Write-CombinedProgress -ObservedBytes $observedBytes -TotalBytes $totalBytes -CompletedFiles $completedFiles `
        -TotalFiles $files.Count -InitialBytes $initialBytes -Stopwatch $stopwatch
}

Write-Progress -Id 1 -Activity 'Updating nine official HyperFrames skills' -Completed

$expectedPaths = @{}
foreach ($item in $files) {
    if (-not (Test-Path -LiteralPath $item.Destination -PathType Leaf)) {
        throw "Validation failed: missing $($item.Destination)"
    }
    $actualSize = (Get-Item -LiteralPath $item.Destination).Length
    if ($actualSize -ne $item.Size) {
        throw "Validation failed: $($item.RepoPath) is $actualSize bytes; expected $($item.Size)."
    }
    $actualSha = Get-GitBlobSha1 -Path $item.Destination
    if ($actualSha -ne $item.Sha) {
        throw "Validation failed: $($item.RepoPath) has Git blob SHA $actualSha; expected $($item.Sha)."
    }
    $expectedPaths[(Get-FullNormalizedPath $item.Destination)] = $true
}

# Remove only stale cache files inside the nine exact downloaded skill directories.
foreach ($skill in $SkillNames) {
    $skillCache = Assert-StrictChildPath -Path (Join-Path $SelectedRoot $skill) -Root $SelectedRoot
    if (-not (Test-Path -LiteralPath $skillCache -PathType Container)) { continue }
    foreach ($cachedFile in Get-ChildItem -LiteralPath $skillCache -Recurse -File) {
        $cachedPath = Get-FullNormalizedPath $cachedFile.FullName
        if (-not $expectedPaths.ContainsKey($cachedPath)) {
            Remove-Item -LiteralPath (Assert-StrictChildPath -Path $cachedPath -Root $SelectedRoot) -Force
        }
    }
}

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupRoot = Join-Path $WorkRoot "backup-$timestamp"
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

foreach ($targetRoot in $TargetRoots) {
    $targetLabel = if ($targetRoot -like '*\.agents\skills') { 'agents' } else { 'claude' }
    $targetBackupRoot = Join-Path $backupRoot $targetLabel
    New-Item -ItemType Directory -Path $targetBackupRoot -Force | Out-Null

    foreach ($skill in $SkillNames) {
        $source = Assert-StrictChildPath -Path (Join-Path $SelectedRoot $skill) -Root $SelectedRoot
        $destination = Assert-StrictChildPath -Path (Join-Path $targetRoot $skill) -Root $targetRoot
        $backup = Assert-StrictChildPath -Path (Join-Path $targetBackupRoot $skill) -Root $backupRoot

        if (Test-Path -LiteralPath $destination -PathType Container) {
            Copy-Item -LiteralPath $destination -Destination $backup -Recurse -Force
        }

        $temporaryDestination = Assert-StrictChildPath -Path (Join-Path $targetRoot ('.' + $skill + '.new.' + [Guid]::NewGuid().ToString('N'))) -Root $targetRoot
        Copy-Item -LiteralPath $source -Destination $temporaryDestination -Recurse -Force

        foreach ($item in ($files | Where-Object Skill -eq $skill)) {
            $copiedFile = Join-Path $temporaryDestination ($item.RelativePath -replace '/', '\')
            if (-not (Test-Path -LiteralPath $copiedFile -PathType Leaf) -or
                (Get-Item -LiteralPath $copiedFile).Length -ne $item.Size -or
                (Get-GitBlobSha1 -Path $copiedFile) -ne $item.Sha) {
                throw "Staged target validation failed: $copiedFile"
            }
        }

        if (Test-Path -LiteralPath $destination) {
            Remove-Item -LiteralPath $destination -Recurse -Force
        }
        Move-Item -LiteralPath $temporaryDestination -Destination $destination
        Write-Host "Installed $skill -> $targetRoot"
    }
}

$summary = @(
    "Installed: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')",
    "Source: $TreeUrl",
    "Skills: $($SkillNames -join ', ')",
    "Files: $($files.Count)",
    "Bytes: $totalBytes",
    "Targets: $($TargetRoots -join ', ')",
    "Backup: $backupRoot"
)
$summaryPath = Join-Path $WorkRoot 'INSTALL_COMPLETE.txt'
$summary | Set-Content -LiteralPath $summaryPath -Encoding UTF8

Write-Host ''
Write-Host "SUCCESS: all nine official HyperFrames skill trees were size-validated and installed into both agent directories."
Write-Host "Backup: $backupRoot"
Write-Host "Marker: $summaryPath"
