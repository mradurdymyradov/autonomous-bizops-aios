$ErrorActionPreference = "Stop"

$InstallDir = "D:\hyperframes\gigaam"
$VenvDir = Join-Path $InstallDir ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$env:UV_CACHE_DIR = Join-Path $InstallDir "uv-cache"

function Get-ResumableFile {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [Parameter(Mandatory = $true)][string]$Label
    )

    for ($Attempt = 1; $Attempt -le 50; $Attempt++) {
        Write-Host "$Label - connection attempt $Attempt/50" -ForegroundColor Cyan
        curl.exe --location --continue-at - --connect-timeout 20 --speed-time 30 --speed-limit 1024 --output $OutputPath $Url
        if ($LASTEXITCODE -eq 0) { return }
        Write-Host "Connection dropped. Resuming the same file in 5 seconds..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }
    throw "$Label download failed after 50 resumable attempts."
}

function Get-ParallelResumableFile {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [Parameter(Mandatory = $true)][long]$TotalBytes,
        [int]$Connections = 6
    )

    if ((Test-Path $OutputPath) -and ((Get-Item $OutputPath).Length -eq $TotalBytes)) {
        Write-Host "Model checkpoint is already complete." -ForegroundColor Green
        return
    }

    $PrefixPath = "$OutputPath.prefix"
    if ((Test-Path $OutputPath) -and -not (Test-Path $PrefixPath)) {
        Move-Item -LiteralPath $OutputPath -Destination $PrefixPath
    }
    if (-not (Test-Path $PrefixPath)) {
        New-Item -ItemType File -Path $PrefixPath | Out-Null
    }

    $PrefixBytes = (Get-Item $PrefixPath).Length
    if ($PrefixBytes -gt $TotalBytes) { throw "Partial model is larger than expected." }
    $Remaining = $TotalBytes - $PrefixBytes
    if ($Remaining -eq 0) {
        Move-Item -LiteralPath $PrefixPath -Destination $OutputPath -Force
        return
    }

    $ChunkBytes = [long](2MB)
    $Parts = @()
    for ($Index = 0; ($PrefixBytes + ($Index * $ChunkBytes)) -lt $TotalBytes; $Index++) {
        $Start = $PrefixBytes + ($Index * $ChunkBytes)
        if ($Start -ge $TotalBytes) { break }
        $End = [Math]::Min($TotalBytes - 1, $Start + $ChunkBytes - 1)
        $PartPath = "$OutputPath.part$($Index.ToString('000'))"
        $Expected = $End - $Start + 1
        if ((Test-Path $PartPath) -and ((Get-Item $PartPath).Length -gt $Expected)) {
            throw "Range part $PartPath is larger than expected."
        }
        $Parts += [PSCustomObject]@{
            Path = $PartPath
            Start = $Start
            End = $End
            Expected = $Expected
        }
    }

    $Worker = {
        param($DownloadUrl, $AssignedPartsSpec)
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        foreach ($PartLine in @($AssignedPartsSpec -split "`n")) {
            $Fields = $PartLine -split "\|", 4
            $PartPath = [string]$Fields[0]
            $RangeStart = [long]$Fields[1]
            $RangeEnd = [long]$Fields[2]
            $ExpectedLength = [long]$Fields[3]
            while ($true) {
                $CurrentLength = if (Test-Path $PartPath) { (Get-Item $PartPath).Length } else { 0 }
                if ($CurrentLength -ge $ExpectedLength) { break }
                $RequestStart = $RangeStart + $CurrentLength
                $NextPath = "$PartPath.next"
                Remove-Item -LiteralPath $NextPath -Force -ErrorAction SilentlyContinue
                & curl.exe --silent --show-error --location --range "$RequestStart-$RangeEnd" --max-time 60 --output $NextPath $DownloadUrl
                if (Test-Path $NextPath) {
                    $Source = [System.IO.File]::OpenRead($NextPath)
                    $Destination = [System.IO.File]::Open(
                        $PartPath,
                        [System.IO.FileMode]::Append,
                        [System.IO.FileAccess]::Write,
                        [System.IO.FileShare]::Read
                    )
                    try { $Source.CopyTo($Destination) } finally {
                        $Destination.Dispose()
                        $Source.Dispose()
                    }
                    Remove-Item -LiteralPath $NextPath -Force
                }
                if ($LASTEXITCODE -ne 0) { Start-Sleep -Seconds 3 }
            }
        }
    }

    $Jobs = @()
    for ($WorkerIndex = 0; $WorkerIndex -lt $Connections; $WorkerIndex++) {
        $Assigned = @()
        for ($PartIndex = $WorkerIndex; $PartIndex -lt $Parts.Count; $PartIndex += $Connections) {
            $Part = $Parts[$PartIndex]
            if ((Test-Path $Part.Path) -and ((Get-Item $Part.Path).Length -eq $Part.Expected)) { continue }
            $Assigned += $Part
        }
        if ($Assigned.Count -gt 0) {
            $AssignedSpec = ($Assigned | ForEach-Object { "$($_.Path)|$($_.Start)|$($_.End)|$($_.Expected)" }) -join "`n"
            $Jobs += Start-Job -ScriptBlock $Worker -ArgumentList $Url, $AssignedSpec
        }
    }

    $PreviousBytes = $PrefixBytes
    $PreviousTime = Get-Date
    while ($Jobs.Count -gt 0 -and (@($Jobs | Where-Object State -eq 'Running').Count -gt 0)) {
        Start-Sleep -Seconds 2
        $Downloaded = $PrefixBytes
        foreach ($Part in $Parts) {
            if (Test-Path $Part.Path) { $Downloaded += (Get-Item $Part.Path).Length }
        }
        $Now = Get-Date
        $Seconds = [Math]::Max(0.1, ($Now - $PreviousTime).TotalSeconds)
        $BytesPerSecond = [Math]::Max(0, ($Downloaded - $PreviousBytes) / $Seconds)
        $RemainingBytes = [Math]::Max(0, $TotalBytes - $Downloaded)
        $Eta = if ($BytesPerSecond -gt 0) { [TimeSpan]::FromSeconds($RemainingBytes / $BytesPerSecond) } else { [TimeSpan]::Zero }
        $Percent = [Math]::Min(100, 100 * $Downloaded / $TotalBytes)
        $Status = "{0:N1}% | {1:N1}/{2:N1} MB | {3:N2} MB/s | ETA {4:hh\:mm\:ss}" -f $Percent, ($Downloaded / 1MB), ($TotalBytes / 1MB), ($BytesPerSecond / 1MB), $Eta
        Write-Progress -Activity "GigaAM v3 E2E CTC ($Connections resumable connections)" -Status $Status -PercentComplete $Percent
        $PreviousBytes = $Downloaded
        $PreviousTime = $Now
    }
    Write-Progress -Activity "GigaAM v3 E2E CTC ($Connections resumable connections)" -Completed

    foreach ($Job in $Jobs) {
        if ($Job.State -ne "Completed") {
            Receive-Job $Job -ErrorAction SilentlyContinue
            throw "A parallel model download worker failed."
        }
        Receive-Job $Job -ErrorAction SilentlyContinue | Out-Null
        Remove-Job $Job
    }

    foreach ($Part in $Parts) {
        if (-not (Test-Path $Part.Path) -or ((Get-Item $Part.Path).Length -ne $Part.Expected)) {
            throw "Model range $($Part.Path) is incomplete."
        }
    }

    $CompletePath = "$OutputPath.complete"
    $Destination = [System.IO.File]::Open($CompletePath, [System.IO.FileMode]::Create)
    try {
        foreach ($SourcePath in @($PrefixPath) + @($Parts.Path)) {
            $Source = [System.IO.File]::OpenRead($SourcePath)
            try { $Source.CopyTo($Destination) } finally { $Source.Dispose() }
        }
    } finally {
        $Destination.Dispose()
    }
    if ((Get-Item $CompletePath).Length -ne $TotalBytes) {
        throw "Combined checkpoint size is incorrect."
    }
    Move-Item -LiteralPath $CompletePath -Destination $OutputPath -Force
    Remove-Item -LiteralPath $PrefixPath -Force
    foreach ($Part in $Parts) { Remove-Item -LiteralPath $Part.Path -Force }
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

Write-Host ""
Write-Host "GigaAM Russian transcription setup" -ForegroundColor Cyan
Write-Host "Install: $InstallDir"
Write-Host "Model:   v3_e2e_ctc (CPU, 220M)"
Write-Host ""

if (-not (Test-Path $PythonExe)) {
    Write-Host "[1/4] Creating isolated Python environment..." -ForegroundColor Yellow
    uv venv --python 3.11 $VenvDir
} else {
    Write-Host "[1/4] Python environment already exists." -ForegroundColor Green
}

Write-Host "[2/4] Installing CPU-only PyTorch..." -ForegroundColor Yellow
$TorchPackage = Join-Path $VenvDir "Lib\site-packages\torch"
$TorchaudioPackage = Join-Path $VenvDir "Lib\site-packages\torchaudio"
if ((Test-Path $TorchPackage) -and (Test-Path $TorchaudioPackage)) {
    Write-Host "CPU-only PyTorch is already installed." -ForegroundColor Green
} else {
    uv pip install --python $PythonExe torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE -ne 0) { throw "CPU PyTorch installation failed." }
}

Write-Host "[3/4] Installing official GigaAM..." -ForegroundColor Yellow
$GigaamPackage = Join-Path $VenvDir "Lib\site-packages\gigaam"
if (Test-Path $GigaamPackage) {
    Write-Host "Official GigaAM package is already installed." -ForegroundColor Green
} else {
    uv pip install --python $PythonExe "gigaam @ git+https://github.com/salute-developers/GigaAM.git"
    if ($LASTEXITCODE -ne 0) { throw "GigaAM package installation failed." }
}

Write-Host "[4/4] Downloading v3_e2e_ctc model with MB, speed, and ETA..." -ForegroundColor Yellow
$ModelDir = Join-Path $InstallDir "models"
$ModelPath = Join-Path $ModelDir "v3_e2e_ctc.ckpt"
$TokenizerPath = Join-Path $ModelDir "v3_e2e_ctc_tokenizer.model"
New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null

Get-ParallelResumableFile -Url "https://cdn.chatwm.opensmodel.sberdevices.ru/GigaAM/v3_e2e_ctc.ckpt" -OutputPath $ModelPath -TotalBytes 442404646 -Connections 12
Get-ResumableFile -Url "https://cdn.chatwm.opensmodel.sberdevices.ru/GigaAM/v3_e2e_ctc_tokenizer.model" -OutputPath $TokenizerPath -Label "Tokenizer"

& $PythonExe -c "import gigaam; gigaam.load_model('v3_e2e_ctc', device='cpu', fp16_encoder=False, use_flash=False, download_root=r'D:\hyperframes\gigaam\models'); print('Model loaded successfully.')"
if ($LASTEXITCODE -ne 0) { throw "GigaAM model validation failed." }

$DoneMarker = Join-Path $InstallDir "INSTALL_COMPLETE.txt"
"Installed $(Get-Date -Format o)" | Set-Content -Path $DoneMarker -Encoding UTF8
Write-Host ""
Write-Host "INSTALL COMPLETE" -ForegroundColor Green
Write-Host "The terminal can now be closed."
