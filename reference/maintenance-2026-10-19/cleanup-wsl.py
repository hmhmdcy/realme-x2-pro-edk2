"""Inventory/apply an explicit, reconstructable build-file allowlist; never images."""
from pathlib import Path
import json, os, subprocess, sys, time

HOME = Path('/home/cy122')
PRIVATE = Path('/mnt/e/edk2-samurai-out/cleanup20261019')
PRIVATE.mkdir(exist_ok=True)
ledger = PRIVATE / 'wsl-cleanup-private.json'
roots = sorted(HOME.glob('pmos-samurai-kernel*/kernel'))
roots += [HOME/'pmos-samurai-rootfs01/kernel', HOME/'x2pro-linux/linux',
          HOME/'x2pro-linux/camera269-full-build-r1', HOME/'x2pro-linux/camera279-isp-build-r1']
sdk = HOME/'x2pro-linux/libcamera214-root/work'
outputs = sorted(sdk.glob('*/src/libcamera-v0.7.2/output'))
outputs = [p for p in outputs if p.parent.parent.parent.name != 'libcamera278-r24-r3-built']

def idle():
    names = subprocess.check_output(['ps','-eo','comm='], text=True).split()
    assert not set(names) & {'make','ninja','cc1','cc1plus','clang','gcc','rustc','ld.lld'}, 'Build active'

def validate(root):
    assert root.is_dir() and not root.is_symlink()
    assert root.resolve().is_relative_to(HOME)
    assert not root.resolve().is_relative_to(HOME/'x2pro-linux/camera279-isp-kernel')
    assert root.resolve() != sdk/'libcamera299-inline/output'
    assert not os.path.ismount(root)

if '--apply' not in sys.argv:
    assert not ledger.exists(), 'Preserve previous receipt'
    idle()
    rows = []
    for root in roots + outputs:
        if not root.exists(): continue
        validate(root)
        # In old kernel trees remove object/archive intermediates only. Keep
        # sources, .git, config, modules, vmlinux, Image, DTBs and symbol maps.
        for base, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if d != '.git' and not Path(base,d).is_symlink()]
            for name in files:
                p = Path(base,name)
                if p.is_symlink() or not p.is_file(): continue
                if p.suffix not in {'.o','.a'}: continue
                s = p.stat()
                rows.append(dict(path=str(p),root=str(root),bytes=s.st_size,mtime_ns=s.st_mtime_ns,removed=False))
    data = dict(started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                kind='obsolete_object_and_archive_intermediates',rows=rows,
                bytes=sum(r['bytes'] for r in rows),free_before=os.statvfs('/').f_bavail*os.statvfs('/').f_frsize,complete=False)
    ledger.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({k:v for k,v in data.items() if k!='rows'}))
    from collections import Counter
    totals=Counter()
    for row in rows: totals[row['root']]+=row['bytes']
    print(json.dumps(totals,indent=2))
else:
    data=json.loads(ledger.read_text()); assert not data['complete']
    idle()
    # A tracked prebuilt is source material, even with an object suffix.
    tracked=set()
    for root in roots:
        if not root.exists(): continue
        result=subprocess.run(['git','-C',str(root),'ls-files','-z'],capture_output=True)
        if result.returncode==0:
            tracked.update(str(root/os.fsdecode(n)) for n in result.stdout.split(b'\0') if n)
    assert not tracked.intersection(row['path'] for row in data['rows']), 'Tracked prebuilt selected'
    for row in data['rows']:
        if row['removed']: continue
        root=Path(row['root']);validate(root)
        p=Path(row['path'])
        assert p.resolve().is_relative_to(root.resolve()) and not p.is_symlink()
        assert p.suffix in {'.o','.a'}
        s=p.stat();assert s.st_size==row['bytes'] and s.st_mtime_ns==row['mtime_ns']
        p.unlink();row['removed']=True
    data.update(complete=True,free_after=os.statvfs('/').f_bavail*os.statvfs('/').f_frsize,
                finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    ledger.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({k:v for k,v in data.items() if k!='rows'}))
