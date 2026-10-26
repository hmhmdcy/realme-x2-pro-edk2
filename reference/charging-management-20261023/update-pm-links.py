"""Apply exact two-module PM dependency update, keeping native USB resident."""
from pathlib import Path
import hashlib
import json
import os
import runpy
import subprocess
import tarfile
import time
import traceback

os.umask(0o077)
ROOT=Path('/root/charging-management-20261023')
OUT=ROOT/'pm-link-update';assert not OUT.exists();OUT.mkdir(mode=0o700)
lock=json.loads((ROOT/'pm-link-update-lock.json').read_text())
assert hashlib.sha256((ROOT/'pm-link-update.tar.gz').read_bytes()).hexdigest()==lock['archive_sha256']
manager=runpy.run_path('/usr/sbin/samurai-charging');live=manager['live']
assert manager['verify']()==lock['old_manifest']
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y'
before=live.state();(OUT/'before-private.json').write_text(json.dumps(before))
backup={};new={};changed=[];failure=None;recovery=None
with tarfile.open(ROOT/'pm-link-update.tar.gz') as tar:
    assert {m.name for m in tar.getmembers()}==set(lock['updated_files'])
    for m in tar.getmembers():
        assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
        target=Path('/')/m.name;backup[target]=target.read_bytes();new[target]=tar.extractfile(m).read()
        if m.name!='usr/share/samurai-charging/manifest.json':
            assert hashlib.sha256(new[target]).hexdigest()==lock['new_manifest']['installed_files'][str(target)]
        else:assert json.loads(new[target])==lock['new_manifest']
        (OUT/(target.name+'.before')).write_bytes(backup[target])

def write(target,content):
    temp=target.with_name(target.name+'.pm-update-next');assert not temp.exists()
    with temp.open('xb') as f:f.write(content);f.flush();os.fsync(f.fileno())
    temp.chmod(0o600);temp.replace(target)

def cmd(*args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=30)
    with (OUT/'commands-private.log').open('a') as f:f.write(repr(args)+'\n'+p.stdout+p.stderr)
    assert p.returncode==0,(args,p.returncode)

try:
    cmd('rc-service','samurai-charging','stop')
    cmd('/usr/sbin/samurai-charging','rollback')
    assert (live.CLIENT/'driver').resolve().name=='mp2650'
    assert not Path('/sys/module/samurai_mp2650').exists() and not Path('/sys/module/samurai_gauge_protection').exists()
    assert Path('/sys/module/samurai_usb_input').exists()
    for target,content in new.items():write(target,content);changed.append(target)
    cmd('depmod','-a',os.uname().release)
    cmd('rc-service','samurai-charging','start');time.sleep(2)
    manager['verify']()
    for name,info in lock['new_manifest']['modules'].items():manager['loaded_matches'](Path(info['target']),name.replace('-','_'))
    data=manager['sample']()
    assert data['valid']==data['protection_ok']==data['desired_enable']==1
    assert not any(data[k] for k in ['error','stop_error','latched','source_inhibit','fault'])
except BaseException:
    failure=traceback.format_exc()
    try:
        cmd('rc-service','samurai-charging','stop')
        if (live.CLIENT/'driver').resolve().name=='samurai-mp2650':cmd('/usr/sbin/samurai-charging','rollback')
        for target in changed:write(target,backup[target])
        cmd('depmod','-a',os.uname().release);cmd('rc-service','samurai-charging','start')
    except BaseException:recovery=traceback.format_exc()
after=live.state();(OUT/'after-private.json').write_text(json.dumps(after))
same=before['camera_pm']==after['camera_pm'] and before['m2m']==after['m2m'] and before['services']==after['services']
result={'terminal':True,'passed':not failure and not recovery and same and after['taint']=='0',
    'camera_services_unchanged':same,'taint':int(after['taint']),'usb_provider_unloaded':False,
    'new_manifest_sha256':hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest(),
    'sample':manager['sample']() if (live.CLIENT/'driver').resolve().name=='samurai-mp2650' else None}
(OUT/'failure-private.json').write_text(json.dumps({'update':failure,'recovery':recovery}))
(OUT/'result.json').write_text(json.dumps(result));print(json.dumps(result),flush=True)
if not result['passed']:raise SystemExit(1)
