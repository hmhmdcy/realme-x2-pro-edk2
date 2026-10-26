"""Privately collect only missing OEM Bluetooth HAL/configs from read-only vendor.

Requires a current coordinated device window and the fresh runtime baseline.
Nothing from vendor is executed and no partition or factory setting is written.
"""
from pathlib import Path
import hashlib
import io
import json
import shlex
import tarfile
from host import PRIVATE, ssh

HERE=Path(__file__).resolve().parent
baseline=json.loads((PRIVATE/'runtime-baseline-private.json').read_text())
CODE=r'''
from pathlib import Path
import gzip,hashlib,io,json,os,subprocess,tarfile
expected=EXPECTED_BOOT
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==expected
root=Path('/var/lib/samurai/bluetooth-20261023-oem')
assert not root.exists(),'Inspect previous collection rather than replaying'
block=Path('/dev/disk/by-partlabel/vendor').resolve()
assert block.name=='sda9'
assert 'PARTNAME=vendor' in Path('/sys/class/block/sda9/uevent').read_text().splitlines()
assert Path('/sys/class/block/sda9/size').read_text().strip()=='3342336'
dev=Path('/sys/class/block/sda9/dev').read_text().strip()
assert not any(l.split()[2]==dev for l in Path('/proc/self/mountinfo').read_text().splitlines())
mount=Path('/run/bluetooth-20261023-vendor-ro');assert not mount.exists()
root.mkdir(mode=0o700);mount.mkdir(mode=0o700);owned=False
members={};missing=[]
try:
    subprocess.run(['mount','-t','ext4','-o','ro,noload,nosuid,nodev,noexec',str(block),str(mount)],check=True,capture_output=True)
    owned=True
    row=next(l for l in Path('/proc/mounts').read_text().splitlines() if l.split()[1]==str(mount))
    options=set(row.split()[3].split(','))
    assert {'ro','nosuid','nodev','noexec'}<=options and ('norecovery' in options or 'noload' in options)
    names=['lib64/libbt-vendor.so','lib64/vendor.qti.bluetooth@1.0.so',
        'lib64/hw/android.hardware.bluetooth@1.0-impl-qti.so','lib64/hw/android.hardware.bluetooth@1.0-impl.so',
        'bin/hw/vendor.qti.bluetooth@1.0-service','bin/hw/android.hardware.bluetooth@1.0-service-qti',
        'etc/bluetooth/bt_vendor.conf','etc/bluetooth/bt_stack.conf']
    names += [str(p.relative_to(mount)) for directory in ['lib64','lib64/hw','bin/hw','etc/bluetooth']
              for p in (mount/directory).glob('*bluetooth*') if p.is_file()]
    raw=io.BytesIO()
    with tarfile.open(fileobj=raw,mode='w') as archive:
        for name in sorted(set(names)):
            path=mount/name
            if not path.is_file():missing.append(name);continue
            assert not path.is_symlink() and path.stat().st_size<=12*1024**2
            data=path.read_bytes();assert sum(v['bytes'] for v in members.values())+len(data)<=32*1024**2
            info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o600;info.mtime=0
            archive.addfile(info,io.BytesIO(data))
            members[name]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    packed=gzip.compress(raw.getvalue(),mtime=0)
    (root/'bluetooth-hal-private.tar.gz').write_bytes(packed)
finally:
    if owned:subprocess.run(['umount',str(mount)],check=True,capture_output=True)
assert not any(l.split()[2]==dev for l in Path('/proc/self/mountinfo').read_text().splitlines())
mount.rmdir()
report=dict(bytes=len(packed),sha256=hashlib.sha256(packed).hexdigest(),members=members,missing=missing,
    readonly_noload_noexec=True,unmounted=True,no_oem_code_executed=True)
(root/'collection-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
'''.replace('EXPECTED_BOOT',repr(baseline['boot_id']))

receipt=PRIVATE/'oem-collection-private.json'
if receipt.exists():
    report=json.loads(receipt.read_text())
    assert report['unmounted'] and report['readonly_noload_noexec']
else:
    q=ssh('python3 -',input=CODE.encode(),timeout=60)
    receipt.write_bytes(q.stdout)
    report=json.loads(q.stdout)
parts=PRIVATE/'oem-hal-parts';parts.mkdir(mode=0o700,exist_ok=True)
for offset in range(0,report['bytes'],65536):
    size=min(65536,report['bytes']-offset)
    name=parts/str(offset)
    if name.exists():
        assert name.stat().st_size==size
        continue
    fetch="from pathlib import Path;import sys;p=Path('/var/lib/samurai/bluetooth-20261023-oem/bluetooth-hal-private.tar.gz');f=p.open('rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d))"%(offset,size)
    q=ssh('python3 -c '+shlex.quote(fetch),timeout=20)
    assert len(q.stdout)==size
    name.write_bytes(q.stdout)
archive=PRIVATE/'bluetooth-hal-private.tar.gz'
data=b''.join((parts/str(offset)).read_bytes() for offset in range(0,report['bytes'],65536))
assert hashlib.sha256(data).hexdigest()==report['sha256']
archive.write_bytes(data)
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tf:
    for entry in tf.getmembers():
        assert entry.isfile() and entry.name in report['members']
        assert hashlib.sha256(tf.extractfile(entry).read()).hexdigest()==report['members'][entry.name]['sha256']
summary=dict(file_count=len(report['members']),readonly_noload_noexec=True,unmounted=True,
             no_oem_code_executed=True,private_archive_verified=True,not_runtime_hfp_validation=True)
(HERE/'oem-collection-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
