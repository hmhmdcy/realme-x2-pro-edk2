"""Additive file install and bounded service validation; run in owned window."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tarfile
import time
import traceback

ROOT=Path('/root/charging-management-20261023')
spec=importlib.util.spec_from_file_location('live',ROOT/'live-session.py')
live=importlib.util.module_from_spec(spec);spec.loader.exec_module(live)
STATE=Path('/var/lib/samurai/charging-managed')
os.umask(0o077)

def command(*args):
    q=subprocess.run(args,capture_output=True,text=True,timeout=25)
    if q.returncode:raise RuntimeError({'args':args,'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr})
    return q.stdout

def install():
    live.guard();assert (live.CLIENT/'driver').resolve().name=='mp2650'
    archive=ROOT/'service-payload.tar.gz'
    with tarfile.open(archive) as tar:
        members={p.name:p for p in tar.getmembers()}
        assert all(p.isfile() and not p.name.startswith('/') and '..' not in Path(p.name).parts for p in members.values())
        manifest_name='usr/share/samurai-charging/manifest.json'
        meta=json.loads(tar.extractfile(manifest_name).read())
        assert meta['release']==os.uname().release
        expected=set(k.lstrip('/') for k in meta['installed_files'])|{manifest_name}
        assert expected==members.keys()
        for name,p in members.items():
            assert p.uid==p.gid==0
            target=Path('/')/name
            assert not target.exists() and not target.is_symlink(),str(target)
            content=tar.extractfile(name).read()
            if name!=manifest_name:assert hashlib.sha256(content).hexdigest()==meta['installed_files']['/'+name]
        STATE.mkdir(mode=0o700,parents=True,exist_ok=True)
        record={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'placed':[],'payload_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'terminal':False}
        receipt=STATE/'install-private.json';assert not receipt.exists()
        receipt.write_text(json.dumps(record))
        for name,p in members.items():
            target=Path('/')/name;target.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
            tmp=target.with_name(target.name+'.charging-next');assert not tmp.exists()
            with tmp.open('xb') as f:
                f.write(tar.extractfile(name).read());f.flush();os.fsync(f.fileno())
            tmp.chmod(p.mode);tmp.rename(target)
            record['placed'].append(str(target));receipt.write_text(json.dumps(record))
        command('depmod','-a',os.uname().release)
        record['terminal']=True;receipt.write_text(json.dumps(record))
    return {'installed_files':len(members),'only_additive_paths':True,'boot_enabled':False}

def test():
    live.guard();out=ROOT/'service-test';assert not out.exists();out.mkdir(mode=0o700)
    before=live.state();(out/'before-private.json').write_text(json.dumps(before))
    result={'terminal':False,'passed':False,'pid':os.getpid()};(out/'state-private.json').write_text(json.dumps(result))
    data={};failure=None;rollback=None
    try:
        data['start']=command('rc-service','samurai-charging','start')
        time.sleep(3)
        assert (live.CLIENT/'driver').resolve().name=='samurai-mp2650'
        d={k:int(v) for k,v in (x.split('=') for x in (live.CLIENT/'telemetry').read_text().split())}
        assert d['valid']==d['protection_ok']==d['desired_enable']==1 and not d['error'] and not d['stop_error']
        assert not d['source_inhibit'] and not d['latched']
        r=live.registers();assert r['02'] & 0x7f == 5 and r['00'] & 0x7f == r['0f'] & 0x7f == 18
        assert r['04']==before['registers']['04'] and r['08'] & 0x18 == 0x10
        assert Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='N'
        data['charging']={'sample':d,'registers':r,'battery_current_ua':int((live.PSY/'bq28z610-0/current_now').read_text())}
        data['stop']=command('rc-service','samurai-charging','stop')
        assert live.registers()['08'] & 0x18 == 8
        data['restart']=command('rc-service','samurai-charging','start')
        assert live.registers()['08'] & 0x18 == 0x10
    except BaseException:failure=traceback.format_exc()
    finally:
        try:
            command('rc-service','samurai-charging','stop')
            if (live.CLIENT/'driver').resolve().name=='samurai-mp2650':
                data['rollback']=command('/usr/sbin/samurai-charging','rollback')
        except BaseException:rollback=traceback.format_exc()
        after=live.state();(out/'after-private.json').write_text(json.dumps(after))
        exact=live.configuration(before)==live.configuration(after)
        unchanged=before['camera_pm']==after['camera_pm'] and before['m2m']==after['m2m'] and before['services']==after['services']
        result.update(terminal=True,passed=not failure and not rollback and exact and unchanged and after['taint']=='0',
            exact_rollback=exact,camera_services_unchanged=unchanged,taint=int(after['taint']))
        (out/'observations-private.json').write_text(json.dumps(data))
        (out/'failure-private.json').write_text(json.dumps({'test':failure,'rollback':rollback}))
        (out/'state-private.json').write_text(json.dumps(result))
    return result

action=sys.argv[1]
if action=='install':result=install()
elif action=='test':result=test()
elif action=='enable':
    assert json.loads((ROOT/'service-test/state-private.json').read_text())['passed']
    command('rc-update','add','samurai-charging','default')
    assert Path('/etc/runlevels/default/samurai-charging').is_symlink()
    result={'boot_enabled':True,'currently_original_observer':(live.CLIENT/'driver').resolve().name=='mp2650'}
else:raise ValueError(action)
print(json.dumps(result))
