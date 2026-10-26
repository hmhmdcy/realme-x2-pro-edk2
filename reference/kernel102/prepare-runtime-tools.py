from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel102';old=root/'reference/kernel101'
assert not (ref/'prepare-package.py').exists()
s=(old/'prepare-package.py').read_text().replace('kernel101','kernel102').replace('k101','k102')
s=s.replace('kernel_build=100,logical_stage=101','kernel_build=101,logical_stage=102')
s=s.replace('91b64b25be666ec62778e96bbb2e67b985c84ac1d84f4dca10c0d0911ac068df','b71044d4cee6190e433878af8bc6be12e8179adcf1219981faeb4309c4406543')
s=s.replace('02554a24fa661c00f2684f8cc1aee3ae57b5887c552bb335d372e8276fbdb9ea','2545f18650669910b1923d99dffbd802bc426438327619890150d98832f3d8fe')
s=s.replace('-adsp.img','-audio.img').replace('Image-adsp','Image-audio').replace('dtb-adsp','dtb-audio').replace('ADSP_CANDIDATE','AUDIO_TRANSPORT_CANDIDATE')
(ref/'prepare-package.py').write_text(s)
for name in ('collect-audio-runtime.sh','collect-boot-failure.sh','recover-after-mpss-crash.sh','test-recovered-network-retry1.sh'):
    assert not (ref/name).exists()
    s=(old/name).read_text().replace('k101','k102').replace('#100 SMP PREEMPT','#101 SMP PREEMPT')
    if name=='collect-audio-runtime.sh':
        anchor='cat /proc/asound/cards > "$dir/alsa-cards.txt"'
        s=s.replace(anchor,anchor+'''\ncat /sys/kernel/debug/pinctrl/3100000.pinctrl/pinmux-pins > "$dir/pinmux.txt"
find /sys/bus/slimbus/devices /sys/bus/platform/drivers/wcd934x-codec /sys/bus/i2c/drivers/max98927 -maxdepth 2 -type l -exec ls -l '{}' ';' > "$dir/codec-bus.txt"
cat /sys/kernel/debug/devices_deferred > "$dir/deferred.txt"
cat /proc/interrupts > "$dir/interrupts.txt"
sha256sum /dev/sde17 > "$dir/stock-dtbo-after.sha"
for p in /sys/class/i2c-adapter/i2c-*; do echo "$p";cat "$p/name"; done > "$dir/i2c-adapters.txt"
''')
    if name=='recover-after-mpss-crash.sh':
        s=s.replace('/usr/sbin/samurai-bluetooth start > "$dir/bt-start.txt" 2>&1','echo USER_BT_REMAINS_OFF > "$dir/bt-start-deferred.txt"')
        s=s.replace('/tmp/k102-bt-mgmt-probe info > "$dir/bt-info.txt"','ls /sys/class/bluetooth > "$dir/bt-class.txt"')
    (ref/name).write_text(s)
print('AUDIO_RUNTIME_TOOLS_PREPARED')
