from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
text=(ref/'observe-radio-clean-reboot.ps1').read_text()
text=text.replace("$BootCheckpoint='first-before-slpi'", "$BootCheckpoint='audio-radio-quiesce-5'")
start=text.index("$command='")
end=text.index('\n& "$PSScriptRoot',start)
text=text[:start]+'''$command='set -eu; uname -v | grep -q "^#113 "; test "$(cat /proc/sys/kernel/random/boot_id)" = "$(cat /var/lib/samurai/k113-{1}/boot-id-private.txt)"; test "$(cat /proc/sys/kernel/tainted)" = 512; test "$(cat /sys/devices/platform/sensor-power/state)" = "vdd=0 vddio=0"; for number in 0 1 2; do test "$(cat /sys/class/remoteproc/remoteproc$number/state)" = offline; done; test -z "$(pgrep -u 10000 || true)"; test -f /var/lib/samurai/k113-{1}/SHA256SUMS; sync; nohup /bin/sh -c "sleep 2; exec /sbin/reboot" > /run/k113-{0}-normal-reboot.log 2>&1 < /dev/null & echo AUDIO_QUIESCED_NORMAL_OPENRC_REBOOT_REQUESTED' -f $Prefix,$BootCheckpoint
''' +text[end:]
text=text.replace("$BootCheckpoint='audio-radio-quiesce-5')", "$BootCheckpoint='audio-radio-quiesce-5', [ValidateSet(0,512)][int]$ExpectedTaint=512)")
text=text.replace(')" = 512;', ')" = {2};')
text=text.replace('-f $Prefix,$BootCheckpoint', '-f $Prefix,$BootCheckpoint,$ExpectedTaint')
(ref/'observe-audio-clean-reboot.ps1').write_text(text)
print('AUDIO_QUIESCED_CURRENT_BOOT_ONLY_NORMAL_REBOOT_PREPARED')
