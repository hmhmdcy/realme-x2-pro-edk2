$ErrorActionPreference='Stop'
$out='E:/edk2-samurai-out/kernel159'
$deadline=[DateTime]::UtcNow.AddSeconds(180)
$source=(Get-Content -Raw -LiteralPath "$out/source-boot-id-private.txt").Trim()
for($i=1;[DateTime]::UtcNow -lt $deadline;$i++) {
    $file="$out/first-observation-$i-private.txt"
    if(Test-Path -LiteralPath $file){throw 'Observation prefix already used'}
    try {
        $state=& "$PSScriptRoot/../kernel109/usb-ssh-pmos.ps1" -Command 'uname -v; cat /proc/sys/kernel/random/boot_id; cat /proc/sys/kernel/tainted; pgrep -u 10000 -x phoc; pgrep -u 10000 -x phosh'
        $state | Set-Content -LiteralPath $file -Encoding utf8NoBOM
        if ($state[0] -notlike '#158 *' -or $state[1] -eq $source -or $state[2] -ne '0') {throw 'New158 identity not established'}
        if ($state.Count -lt 5) {throw 'Desktop still starting'}
        $state[1] | Set-Content -LiteralPath "$out/first-boot-id-private.txt" -Encoding utf8NoBOM
        Write-Output K159_NEW_BOOT_DESKTOP_PRESENT
        exit 0
    } catch {$_.Exception.Message | Add-Content -LiteralPath $file}
    Start-Sleep -Seconds 4
}
throw 'New158 runtime not confirmed in observation window'
