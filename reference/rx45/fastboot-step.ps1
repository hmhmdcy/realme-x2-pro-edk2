param([Parameter(Mandatory=$true)][ValidateSet('Product','FlashMask','FlashBaseline')][string]$Action)
$ErrorActionPreference='Stop'
$taskJob=Start-Job -ArgumentList $Action -ScriptBlock {
    param($step)
    $exe='C:\Users\cy122\Downloads\platform-tools\platform-tools\fastboot.exe'
    switch ($step) {
        'Product' { & $exe -s 62bc28a1 getvar product 2>&1 }
        'FlashMask' { & $exe -s 62bc28a1 flash logdump 'E:\edk2-samurai-out\logdump-rx45-rx-mask.img' 2>&1 }
        'FlashBaseline' { & $exe -s 62bc28a1 flash logdump 'E:\edk2-samurai-out\logdump-rx44-rx-stats-ctrl-u.img' 2>&1 }
    }
    if ($LASTEXITCODE) { throw "fastboot $step failed: $LASTEXITCODE" }
}
try {
    if (!(Wait-Job $taskJob -Timeout 20)) { throw "fastboot $Action timeout" }
    $result=Receive-Job $taskJob -ErrorAction Stop | Out-String
    Write-Output $result
    if ($Action -eq 'Product' -and $result -notmatch 'product: msmnile') { throw 'Unexpected device product' }
} finally {
    if ($taskJob.State -eq 'Running') { Stop-Job $taskJob }
    Remove-Job $taskJob
}
