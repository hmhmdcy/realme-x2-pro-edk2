from pathlib import Path
import json
root=Path('/mnt/e/RealmeX2Pro edk2')
ref=root/'reference/kernel102'; old=root/'reference/kernel101'
out=Path('/mnt/e/edk2-samurai-out/kernel102')
names=['build-firmware.sh','verify-firmware.py','collect-preflash.sh','split-backups.sh',
       'receive-backups.ps1','scp-private.ps1','reboot-f1.ps1','read-eud.ps1','stop-connectivity.sh']
assert all(not (ref/n).exists() for n in names)
for name in names:
    s=(old/name).read_text().replace('kernel101','kernel102').replace('k101','k102')
    s=s.replace('Image-adsp','Image-audio').replace('dtb-adsp','dtb-audio').replace('-adsp.img','-audio.img')
    if name=='verify-firmware.py':s=s.replace('adsp_and_apr_core_only','samurai_audio_transport_only')
    if name=='split-backups.sh':s=s.replace('#99 SMP PREEMPT','#100 SMP PREEMPT')
    if name=='collect-preflash.sh':
        s=s.replace('#99 SMP PREEMPT','#100 SMP PREEMPT')
        s=s.replace('7fa3a6879f8e3409fff129befedc32c6e67785fac18665984f52bf2d0f067c1f','ea123f3aa112f477d979444f5d620b4b378ef09ef2f55c140658b65407b57cc0')
        s=s.replace('02554a24fa661c00f2684f8cc1aee3ae57b5887c552bb335d372e8276fbdb9ea','2545f18650669910b1923d99dffbd802bc426438327619890150d98832f3d8fe')
        s=s.replace('    cat /sys/class/remoteproc/remoteproc0/state','    for p in /sys/class/remoteproc/remoteproc*; do cat "$p/name" "$p/state"; done')
    if name=='stop-connectivity.sh':
        s=s.replace('[ "$(cat /sys/class/remoteproc/remoteproc0/state)" = running ]','mpss=$(/usr/sbin/samurai-modem-remoteproc)\n[ "$(cat "$mpss/state")" = running ]')
        s=s.replace('/sys/class/remoteproc/remoteproc0/','$mpss/')
    (ref/name).write_text(s)
flash=(old/'flash-adsp.ps1').read_text().replace('kernel101','kernel102').replace('k101','k102').replace('K101','K102').replace('-adsp.img','-audio.img').replace('$audit.kernel_build -ne 100','$audit.kernel_build -ne 101')
assert not (ref/'flash-audio.ps1').exists()
(ref/'flash-audio.ps1').write_text(flash)
# Identity stays private and is re-confirmed independently before flashing.
assert not (out/'fastboot-identity.json').exists()
(out/'fastboot-identity.json').write_bytes((out.parent/'kernel101/fastboot-identity.json').read_bytes())
print('AUDIO_DEPLOYMENT_TOOLS_PREPARED')
