from pathlib import Path
import json,re,shutil
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel107';old=root/'reference/kernel106';out=Path('/mnt/e/edk2-samurai-out/kernel107');prev=out.parent/'kernel106'
c=json.loads((prev/'candidate-validation.json').read_text())
names=['collect-preflash.sh','split-backups.sh','receive-backups.ps1','scp-private.ps1','stop-connectivity.sh','reboot-f1.ps1','read-eud.ps1','haptics-device','collect-audio-runtime.sh','collect-first-radio-trace.sh','collect-boot-failure.sh','recover-after-mpss-crash.sh','test-auto-network.sh','test-playback.sh','test-capture-dmic.sh','flash-radio.ps1','analyse-trace.py','inspect-radio-order.py']
for n in names:
    assert not (ref/n).exists()
    s=(old/n).read_text().replace('kernel106','kernel107').replace('k106','k107').replace('K106','K107')
    s=s.replace('#105 SMP PREEMPT','#106 SMP PREEMPT')
    if n in ['collect-preflash.sh','split-backups.sh']:s=s.replace('#104 SMP PREEMPT','#105 SMP PREEMPT')
    if n=='collect-preflash.sh':
        hashes=re.findall(r"grep -q '\^([a-f0-9]{64}) ",s);assert len(hashes)==2
        s=s.replace(hashes[0],c['boot_sha256']).replace(hashes[1],c['logdump_sha256'])
    if n=='flash-radio.ps1':s=s.replace('$audit.kernel_build -ne 105','$audit.kernel_build -ne 106')
    (ref/n).write_text(s)
n='prepare-package.py';s=(old/n).read_text().replace('kernel106','kernel107').replace('k106','k107')
s=s.replace("prev=out.parent/'kernel105'","prev=out.parent/'kernel106'").replace('kernel_build=105','kernel_build=106').replace('logical_stage=106','logical_stage=107')
assert not (ref/n).exists();(ref/n).write_text(s)
for n in ['fastboot-identity.json','wpa-5g-private.conf','tinymix','tinyplay','tinycap','tone-low-private.wav']:
    assert not (out/n).exists();shutil.copyfile(prev/n,out/n)
print('STAGE107_FRESH_DEPLOYMENT_AND_BOUNDED_TEST_TOOLS_PREPARED')
