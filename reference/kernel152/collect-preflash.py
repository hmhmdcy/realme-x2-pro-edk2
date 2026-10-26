from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

os.umask(0o077)
out=Path('/var/lib/samurai/k152-preflash')
assert os.uname().version.startswith('#147 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==Path('/tmp/k152-source-boot-id-private.txt').read_text().strip()
if out.exists():
    assert (out / 'boot-id-private.txt').read_bytes() == Path('/proc/sys/kernel/random/boot_id').read_bytes()
else:
    out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())

def capture(args,name):
    (out / name).write_bytes(subprocess.check_output(args))

capture(['dmesg'],'dmesg-private.txt')
prior=(out / 'dmesg-private.txt').read_text()
assert prior.count('WARNING:')==0
assert prior.count('gpu fault:')==3
capture(['uname','-a'],'kernel.txt')
capture(['lsblk','-b','-o','NAME,SIZE,PARTLABEL'],'partitions-private.txt')
for dev,part,size in [('sde11','boot',100663296),('sde32','logdump',67108864)]:
    actual=subprocess.check_output(['lsblk','-ndo','PARTLABEL','/dev/'+dev],text=True).strip()
    assert actual==part, (dev,actual)
    actual_size=int(subprocess.check_output(['blockdev','--getsize64','/dev/'+dev],text=True))
    if part=='logdump': assert actual_size==size
capture(['sha256sum','/dev/sde11','/dev/sde32','/dev/sda2'],'partition-check.sha256')
capture(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],'nv-check.txt')
shutil.copyfile('/var/lib/samurai/k132-preflash/new-module-tree.sha256',out / 'old132-module-tree.sha256')
capture(['cat','/sys/kernel/debug/dri/1/state'],'drm-private.txt')
capture(['cat','/sys/class/remoteproc/remoteproc0/state','/sys/class/remoteproc/remoteproc1/state','/sys/class/remoteproc/remoteproc2/state'],'remoteprocs.txt')
capture(['cat','/sys/devices/platform/sensor-power/state'],'sensor-power.txt')
pcm = list(Path('/proc/asound').glob('card*/pcm*/sub*/status'))
states = {str(x): x.read_text() for x in pcm}
assert all(x.strip() == 'closed' for x in states.values())
(out / 'pcm-state-private.json').write_text(json.dumps(states, indent=2) + '\n')
capture(['cat','/proc/asound/cards'],'soundcards.txt')
capture(['cat','/sys/bus/i2c/devices/1-0039/status','/sys/bus/i2c/devices/1-003a/status'],'amps.txt')
subprocess.run(['tar','-C',str(out),'-czf','/tmp/k152-preflash-private.tar.gz','.'],check=True)
print('K152_CURRENT147_PREFLASH_CAPTURED')
