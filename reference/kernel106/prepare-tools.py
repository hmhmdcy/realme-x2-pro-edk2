from pathlib import Path
import json,re,shutil
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel106';old=root/'reference/kernel105'
out=Path('/mnt/e/edk2-samurai-out/kernel106');prev=out.parent/'kernel105'
c=json.loads((prev/'candidate-validation.json').read_text())
names=['collect-preflash.sh','split-backups.sh','receive-backups.ps1','scp-private.ps1','stop-connectivity.sh','reboot-f1.ps1','read-eud.ps1','haptics-device','collect-audio-runtime.sh','test-core-rebind-once.sh','collect-boot-failure.sh','recover-after-mpss-crash.sh','test-auto-network.sh','flash-radio.ps1']
for n in names:
    assert not (ref/n).exists()
    s=(old/n).read_text().replace('kernel105','kernel106').replace('k105','k106').replace('K105','K106')
    s=s.replace('#104 SMP PREEMPT','#105 SMP PREEMPT')
    if n in ['collect-preflash.sh','split-backups.sh']:
        s=s.replace('#103 SMP PREEMPT','#104 SMP PREEMPT')
    if n=='collect-preflash.sh':
        hashes=re.findall(r"grep -q '\^([a-f0-9]{64}) ",s)
        assert len(hashes)==2
        s=s.replace(hashes[0],c['boot_sha256']).replace(hashes[1],c['logdump_sha256'])
    if n=='flash-radio.ps1':s=s.replace('$audit.kernel_build -ne 104','$audit.kernel_build -ne 105')
    (ref/n).write_text(s)
for n in ['fastboot-identity.json','wpa-5g-private.conf']:
    assert not (out/n).exists();shutil.copyfile(prev/n,out/n)
print('STAGE106_FRESH_FLASH_AND_RUNTIME_TOOLS_PREPARED')
