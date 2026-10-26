from pathlib import Path
import json
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel103';old=root/'reference/kernel102'
out=Path('/mnt/e/edk2-samurai-out/kernel103');prev=out.parent/'kernel102'
audit=json.loads((prev/'candidate-validation.json').read_text())
names=['build-firmware.sh','verify-firmware.py','collect-preflash.sh','split-backups.sh','receive-backups.ps1',
       'scp-private.ps1','reboot-f1.ps1','read-eud.ps1','stop-connectivity.sh','flash-audio.ps1','haptics-device']
for name in names:
    assert not (ref/name).exists()
    s=(old/name).read_text().replace('kernel102','kernel103').replace('k102','k103').replace('K102','K103')
    s=s.replace('#100 SMP PREEMPT','#101 SMP PREEMPT')
    if name=='collect-preflash.sh':
        s=s.replace('cat /sys/bus/i2c/devices/1-005a/status','cat "$(/tmp/k103-haptics-device)/status"')
        s=s.replace('head -c 6680576','head -c '+str(audit['boot_bytes']))
        s=s.replace('ea123f3aa112f477d979444f5d620b4b378ef09ef2f55c140658b65407b57cc0',audit['boot_sha256'])
        s=s.replace('2545f18650669910b1923d99dffbd802bc426438327619890150d98832f3d8fe',audit['logdump_sha256'])
    if name=='flash-audio.ps1':s=s.replace('$audit.kernel_build -ne 101','$audit.kernel_build -ne 102')
    (ref/name).write_text(s)
(out/'fastboot-identity.json').write_bytes((prev/'fastboot-identity.json').read_bytes())
print('FRESH_K103_DEPLOYMENT_TOOLS_PREPARED')
