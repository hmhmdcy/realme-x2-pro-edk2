$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel152'
$deadline=[DateTime]::UtcNow.AddSeconds(180)
for($i=1;[DateTime]::UtcNow -lt $deadline;$i++) {
    $file="$out/rollback147-observation-$i-private.txt"
    if(Test-Path -LiteralPath $file){throw 'Observation prefix already used'}
    try {
        $state=& "$PSScriptRoot/../kernel109/usb-ssh-pmos.ps1" -Command 'uname -v; cat /proc/sys/kernel/random/boot_id; cat /proc/sys/kernel/tainted; pgrep -u 10000 -x phoc; pgrep -u 10000 -x phosh'
        $state | Set-Content -LiteralPath $file -Encoding utf8NoBOM
        if ($state[0] -notlike '#147 *') {throw 'Unexpected kernel'}
        $source=(Get-Content -Raw -LiteralPath "$out/source-boot-id-private.txt").Trim()
        $failed=(Get-Content -Raw -LiteralPath "$out/failed-boot-id-private.txt").Trim()
        if ($state[1] -eq $source -or $state[1] -eq $failed -or $state[2] -ne '0') {throw 'New stable boot identity not established'}
        if ($state.Count -lt 5) {throw 'Desktop still starting'}
        $state[1] | Set-Content -LiteralPath "$out/rollback147-boot-id-private.txt" -Encoding utf8NoBOM
        Write-Output K152_NEW147_DESKTOP_RESTORED
        exit 0
    } catch {
        $_.Exception.Message | Add-Content -LiteralPath $file
    }
    Start-Sleep -Seconds 4
}
throw 'Rollback runtime not confirmed within observation window'
