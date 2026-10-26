from pathlib import Path
import shutil, subprocess
root=Path('/mnt/e/RealmeX2Pro edk2')
ref=root/'reference/kernel101'
out=Path('/mnt/e/edk2-samurai-out/kernel101')
assert not (ref/'recover-after-mpss-crash.sh').exists()
for name in ('collect-boot-failure.sh','recover-after-mpss-crash.sh','test-recovered-network.sh'):
    text=(root/'reference/kernel100'/name).read_text().replace('k100','k101').replace('#99 SMP PREEMPT','#100 SMP PREEMPT')
    text=text.replace('uname -a | grep -q \'#100 SMP PREEMPT\'\n',
      'uname -a | grep -q \'#100 SMP PREEMPT\'\nmpss=$(/usr/sbin/samurai-modem-remoteproc)\n')
    text=text.replace('/sys/class/remoteproc/remoteproc0/','$mpss/')
    if name=='collect-boot-failure.sh':
        text=text.replace('for name in tftp.log rmtfs.log', 'for name in wpa.log tftp.log rmtfs.log')
    if name=='recover-after-mpss-crash.sh':
        text=text.replace('dir=/tmp/k101-radio-recovery-first', '''grep -qx 0 /tmp/k101-audio-runtime/native-api-exit.txt
adsp=$(cat /tmp/k101-audio-runtime/adsp-path.txt)
[ "$(cat "$adsp/state")" = running ]
test ! -d /run/samurai-bluetooth/lifecycle.lock
test ! -S /run/samurai-wifi/wpa-control/wlan0
dir=/tmp/k101-radio-recovery-first''')
        text=text.replace('    [ "$(cat /proc/sys/kernel/tainted)" = 0 ]','    [ "$(cat /proc/sys/kernel/tainted)" = 0 ]\n    [ "$(cat "$adsp/state")" = running ]')
        text=text.replace('dmesg > "$dir/dmesg-after.txt"','cat /sys/bus/aprbus/devices/*/samurai_api > "$dir/native-api-after.txt"\ndmesg > "$dir/dmesg-after.txt"')
    (ref/name).write_text(text)
    subprocess.run(['sh','-n',str(ref/name)],check=True)
shutil.copyfile(out.parent/'kernel98/bt-mgmt-probe-scan-window',out/'bt-mgmt-probe-private')
shutil.copyfile(out.parent/'kernel100/wpa-private.conf',out/'wpa-private.conf')
print('ADSP_PRESERVING_BOUNDED_RADIO_RECOVERY_PREPARED')
