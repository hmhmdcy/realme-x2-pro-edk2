"""Write only the prepared FAT image after the one planned reboot and fresh identity checks."""
from pathlib import Path
import hashlib,json,re,subprocess,time
import host

ROOT=Path(__file__).resolve().parent;PRIVATE=host.PRIVATE
assert (PRIVATE/'reboot-request-private.json').exists()
package=json.loads((ROOT/'boot-package-validation.json').read_text())
assert package['planned_flash_partitions']==['logdump'] and package['kernel_build']==363
lock=json.loads((PRIVATE/'deployment-lock-private.json').read_text())
for row in lock['files'].values():
 p=Path(row['path']);assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
image=Path(lock['files']['candidate']['path']);assert image.stat().st_size==67108864
assert not (PRIVATE/'flash-request-private.json').exists()
fb='/mnt/c/Users/cy122/Downloads/platform-tools/platform-tools/fastboot.exe'
def command(args,name):
 q=subprocess.run([fb,*args],capture_output=True,timeout=50)
 p=PRIVATE/(name+'-r2-private.log');assert not p.exists();p.write_bytes(q.stdout+q.stderr)
 assert q.returncode==0,'Inspect the current transport/device state before any next action'
 return (q.stdout+q.stderr).decode()
deadline=time.monotonic()+40;attempt=0
while True:
 attempt+=1;text=command(['devices'],'devices-'+str(attempt))
 found=re.findall(r'(?m)^(\S+)\s+fastboot\s*$',text)
 if found or time.monotonic()>=deadline:break
 time.sleep(2)
assert len(found)==1
expected=json.loads((PRIVATE.parent/'kernel109/fastboot-identity.json').read_text())['serial']
assert found[0]==expected;serial=found[0]
assert re.search(r'product:\s*msmnile\b',command(['-s',serial,'getvar','product'],'product'))
for part,size in [('boot',100663296),('logdump',67108864)]:
 text=command(['-s',serial,'getvar','partition-size:'+part],'size-'+part)
 match=re.search(r'partition-size:'+part+r':\s*(0x[0-9a-fA-F]+)',text)
 assert match and int(match[1],16)==size
(PRIVATE/'flash-request-private.json').write_text(json.dumps(dict(request_count=1,serial=serial,partition='logdump',sha256=package['logdump_sha256'])))
windows='E:/'+str(image)[len('/mnt/e/'):]
text=command(['-s',serial,'flash','logdump',windows],'flash-logdump')
assert re.search(r"Writing 'logdump'\s+OKAY",text) and 'FAILED' not in text
report=dict(stage=365,fresh_fastboot_identity_and_geometry_verified=True,logdump_flash_success=True,
            logdump_sha256=package['logdump_sha256'],partitions_flashed=['logdump'],boot_not_flashed=True,runtime_readback_pending=True)
(ROOT/'flash-validation.json').write_text(json.dumps(report,indent=2)+'\n')
marker=PRIVATE/'fastboot-reboot-request-private.json';assert not marker.exists()
marker.write_text(json.dumps(dict(request_count=1,serial=serial)))
command(['-s',serial,'reboot'],'fastboot-reboot')
print(json.dumps(report,indent=2))
