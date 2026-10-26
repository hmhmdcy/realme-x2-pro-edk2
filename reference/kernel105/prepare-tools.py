from pathlib import Path
import json, shutil
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel105';old=root/'reference/kernel104'
out=Path('/mnt/e/edk2-samurai-out/kernel105');prev=out.parent/'kernel104'
c=json.loads((prev/'candidate-validation.json').read_text())
for n in ['collect-preflash.sh','split-backups.sh','receive-backups.ps1','scp-private.ps1',
          'stop-connectivity.sh','reboot-f1.ps1','read-eud.ps1','haptics-device',
          'collect-audio-runtime.sh','test-core-rebind-once.sh','collect-boot-failure.sh',
          'recover-after-mpss-crash.sh','test-auto-network.sh']:
    assert not (ref/n).exists()
    s=(old/n).read_text().replace('kernel104','kernel105').replace('k104','k105').replace('K104','K105')
    if n in ('collect-preflash.sh','split-backups.sh'):
        s=s.replace('#102 SMP PREEMPT','#103 SMP PREEMPT')
    else:
        s=s.replace('#103 SMP PREEMPT','#104 SMP PREEMPT')
    if n=='collect-preflash.sh':
        s=s.replace('head -c 6682624','head -c '+str(c['boot_bytes']))
        s=s.replace('301a958c440cadecd8d465c7c3f1918860b61fc0ee665410bc3632f9a45e3048',c['boot_sha256'])
        s=s.replace('244130230b6aa495aa82b8110071594d72dbce67bd002ad271cee4aa38ce0050',c['logdump_sha256'])
    (ref/n).write_text(s)
for n in ['fastboot-identity.json','wpa-5g-private.conf']:
    assert not (out/n).exists()
    shutil.copyfile(prev/n,out/n)
print('STAGE105_FRESH_GUARDED_TOOLS_PREPARED')
