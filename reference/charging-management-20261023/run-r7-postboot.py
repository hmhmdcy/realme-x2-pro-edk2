"""Read the new boot with the original pinned key; adopt only a passed baseline."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import shlex

REF=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OUT=PRIVATE/'r7-postboot'
CANDIDATE=REF.parent/'charging-oem-audit-20261023/normal-restart-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def durable_create(p,raw):
    with p.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())


def main(action):
    OUT.mkdir(mode=0o700,exist_ok=True)
    spec=importlib.util.spec_from_file_location('window',REF/'device-window.py')
    window=importlib.util.module_from_spec(spec);spec.loader.exec_module(window)
    previous=json.loads((PRIVATE/'r7-restart/prepare-stdout-private.json').read_text())['guard']
    assert (PRIVATE/'r7-restart/restart-request-private.json').exists()
    fastboot_reboot_dispatched=(PRIVATE/'r7-restart/fastboot-reboot-request-private.json').exists()
    if action=='observe':
        tested=json.loads((CANDIDATE/'r7-postboot-test-result.json').read_text())
        worker=(CANDIDATE/'r7-postboot.py').read_bytes()
        assert tested['passed'] and tested['candidate_sha256']==sha(worker)
        expected={'EXPECTED_CAMERA':json.loads((REF.parent/'kernel440/current-state-validation.json').read_text()),
                  'OLD_BOOT_UUID':previous['boot_id'],'EXPECTED_KERNEL_RELEASE':previous['kernel_release'],
                  'EXPECTED_KERNEL_VERSION':previous['kernel_version'],
                  'EXPECTED_ROOTFS_SHA256':previous['rootfs_release_sha256'],
                  'ORIGINAL_KEY_TRANSPORT_VERIFIED':True,'READ_PMIC_STATUS':True}
        code='globals().update('+repr(expected)+')\n'+worker.decode()
        q=window.host.raw_ssh('python3 -',input=code.encode(),timeout=45,check=False)
        # Repeated read-only snapshots get separate files and retain failures.
        index=1
        while (OUT/('observation-'+str(index)+'-private.json')).exists():index+=1
        target=OUT/('observation-'+str(index)+'-private.json')
        durable_create(target,q.stdout)
        durable_create(OUT/('observation-'+str(index)+'-stderr-private.txt'),q.stderr)
        if not q.stdout:
            print(q.stderr.decode(errors='replace')[-2000:]);return q.returncode or 1
        data=json.loads(q.stdout)
        (OUT/'latest-observation-private.json').write_bytes(q.stdout)
        public=data['result'];public.update(scope='new-boot R7 activation and source baseline',
                    image_rebuilt=False,partitions_written=[],physical_full_recharge_accepted=False,
                    pm_resume_failure_resolved=False,fastboot_reboot_dispatched=fastboot_reboot_dispatched)
        raw=data.get('raw',{})
        public['source_pmic_status']=raw.get('pmic_status')
        public['source_float_currently_observed']=(raw.get('pmic_status',{}).get('0x1308')==0x10)
        (REF/'r7-postboot-result.json').write_text(json.dumps(public,indent=2)+'\n')
        print(json.dumps(public,indent=2))
        if q.returncode:print(q.stderr.decode(errors='replace')[-1500:])
        return q.returncode
    data=json.loads((OUT/'latest-observation-private.json').read_text())
    assert data['result']['passed'],'Only a fully passed observed baseline can be adopted'
    raw=data['raw'];boot=raw['boot_id']
    guard_path='/var/lib/samurai/'+previous['transaction_id']+'-adopted/boot-id-private.txt'
    incoming={'boot':boot,'release':previous['kernel_release'],'version':previous['kernel_version'],
              'rootfs':previous['rootfs_release_sha256'],'guard':guard_path,
              'notes':{n:entry['loaded_note_sha256'] for n,entry in raw['charging_modules'].items()},
              'camera_notes':{n:entry['loaded_note_sha256'] for n,entry in raw['camera_modules'].items()}}
    durable_create(OUT/'adopt-request-private.json',json.dumps(incoming,indent=2).encode())
    code=r'''from pathlib import Path
import hashlib,json,os,sys
data=json.loads(sys.stdin.buffer.read());sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==data['boot']
assert os.uname().release==data['release'] and os.uname().version==data['version']
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert sha(Path('/etc/samurai-rootfs-release').read_bytes())==data['rootfs']
assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())=='5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68'
for name,digest in {**data['notes'],**data['camera_notes']}.items():
 assert sha(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes())==digest
p=Path(data['guard']);assert not p.exists() and not p.parent.exists()
os.umask(0o077);p.parent.mkdir(mode=0o700)
with p.open('x') as f:f.write(data['boot']+'\n');f.flush();os.fsync(f.fileno())
fd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
try:os.fsync(fd)
finally:os.close(fd)
assert p.read_text().strip()==data['boot']
print(json.dumps({'guard_created':True,'original_guard_preserved':True}))
'''
    q=window.host.raw_ssh('python3 -c '+shlex.quote(code),input=json.dumps(incoming).encode(),timeout=20,check=False)
    durable_create(OUT/'adopt-stdout-private.json',q.stdout)
    durable_create(OUT/'adopt-stderr-private.txt',q.stderr)
    if q.returncode:
        print(q.stderr.decode(errors='replace')[-1800:]);return q.returncode
    assert json.loads(q.stdout)['guard_created']
    pointer=PRIVATE/'boot-adoption-private.json'
    durable_create(OUT/'boot-adoption-before-r7-private.json',pointer.read_bytes())
    adoption={'guard_path':guard_path,'original_key_verified':True,'baseline440_verified':True,
              'charging_manifest_sha256':'5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68'}
    temporary=pointer.with_name('boot-adoption-r7-next-private.json')
    durable_create(temporary,json.dumps(adoption,indent=2).encode());temporary.replace(pointer)
    fd=os.open(PRIVATE,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    print(json.dumps({'new_boot_adopted':True,'old_guard_preserved':True,'baseline_passed':True}))
    return 0


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['observe','adopt'])
    raise SystemExit(main(p.parse_args().action))
