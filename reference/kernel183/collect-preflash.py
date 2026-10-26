from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

os.umask(0o077)
out=Path('/var/lib/samurai/k183-preflash')
assert os.uname().version.startswith('#181 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
# Capture a fresh current boot; all subsequent operations compare this exact identity.
if out.exists():
    assert (out / 'boot-id-private.txt').read_bytes() == Path('/proc/sys/kernel/random/boot_id').read_bytes()
else:
    out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())

def capture(args,name):
    (out / name).write_bytes(subprocess.check_output(args))

(out / 'start-uptime-private.txt').write_text(Path('/proc/uptime').read_text())
capture(['dmesg'],'dmesg-private.txt')
prior=(out / 'dmesg-private.txt').read_text()
assert prior.count('WARNING:')==0
assert prior.count('Oops:')==0
assert prior.count('SLIMBUS_0_RX: ASoC error (-22)')==0
# Known audio failures are recorded, not reset or treated as a new healthy boot.
assert prior.count('gpu fault:')==0
capture(['uname','-a'],'kernel.txt')
capture(['lsblk','-b','-o','NAME,SIZE,PARTLABEL'],'partitions-private.txt')
for dev,part,size in [('sde11','boot',100663296),('sde32','logdump',67108864)]:
    actual=subprocess.check_output(['lsblk','-ndo','PARTLABEL','/dev/'+dev],text=True).strip()
    assert actual==part, (dev,actual)
    actual_size=int(subprocess.check_output(['blockdev','--getsize64','/dev/'+dev],text=True))
    assert actual_size==size
capture(['sha256sum','/dev/sde11','/dev/sde32','/dev/sda2'],'partition-check.sha256')

hashes=dict((line.split()[1],line.split()[0]) for line in (out/'partition-check.sha256').read_text().splitlines())
assert hashes['/dev/sde11']=='77e1a272741aeb09f780a1cff1224098bc78126f1a9154ed5d0c00d91f587a28'
assert hashes['/dev/sde32']=='56aa1c463d118f9de8d5dbd2cad3dc6b2ab1ff9f36d4027c77d457520b702a55'
assert hashes['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
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
subprocess.run(['tar','-C',str(out),'-czf','/tmp/k183-preflash-private.tar.gz','.'],check=True)
print('K183_CURRENT181_PREFLASH_CAPTURED')
