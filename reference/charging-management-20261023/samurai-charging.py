#!/usr/bin/python3
"""Board-specific OpenRC entry point; the kernel owns the charging loop."""
from pathlib import Path
import fcntl
import hashlib
import importlib.util
import json
import os
import struct
import subprocess
import sys
import time

LIB=Path('/usr/lib/samurai-charging')
MANIFEST=Path('/usr/share/samurai-charging/manifest.json')
STATE=Path('/var/lib/samurai/charging-managed')
spec=importlib.util.spec_from_file_location('charging_trial_library',LIB/'control-trial.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
live=t.live

def loaded_matches(path,name):
    raw=path.read_bytes();off=struct.unpack_from('<Q',raw,40)[0]
    stride,count,strings=struct.unpack_from('<HHH',raw,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*stride) for i in range(count)]
    names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
    note=next(s for s in sections if names[s[0]:].split(b'\0')[0]==b'.note.gnu.build-id')
    assert Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()==raw[note[4]:note[4]+note[5]]

def verify():
    assert os.geteuid()==0
    assert b'realme,samurai' in Path('/sys/firmware/devicetree/base/compatible').read_bytes().split(b'\0')
    meta=json.loads(MANIFEST.read_text());assert os.uname().release==meta['release']
    for path,digest in meta['installed_files'].items():
        p=Path(path);assert p.is_file() and not p.is_symlink()
        assert p.stat().st_uid==0 and not p.stat().st_mode & 0o022
        assert hashlib.sha256(p.read_bytes()).hexdigest()==digest,path
    return meta

def load_module(meta,name,args):
    path=Path(meta['modules'][name]['target'])
    module=name.replace('-','_')
    if not Path('/sys/module',module).exists():live.run('insmod',str(path),*args)
    loaded_matches(path,module)

def sample():
    return {k:int(v) for k,v in (x.split('=') for x in (live.CLIENT/'telemetry').read_text().split())}

def request(psy,name,value):
    try:(psy/name).write_text(value)
    except OSError:
        d=sample()
        if not (d['source_inhibit'] and not d['latched'] and not d['stop_error']):raise

def inhibit(psy):
    try:(psy/'charge_behaviour').write_text('inhibit-charge')
    except OSError:
        # Policy acquisition can fail after a successful synchronous stop.
        # Only a real hardware readback may establish that normal pause held.
        assert live.registers()['08'] & 0x18 == 8
    assert live.registers()['08'] & 0x18 == 8

def command(meta,action):
    STATE.mkdir(mode=0o700,parents=True,exist_ok=True)
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    psy=live.PSY/'mp2650-input'
    driver=(live.CLIENT/'driver').resolve().name
    if action in ['start','resume']:
        load_module(meta,'samurai-usb-input',['register_board=1'])
        load_module(meta,'samurai-gauge-protection',['register_board=1'])
        if driver=='mp2650':
            before=live.state()
            p=STATE/'original-install-private.json'
            if not p.exists():
                with p.open('x') as f:json.dump(before,f);f.flush();os.fsync(f.fileno())
            current=STATE/('before-'+boot+'-private.json')
            if not current.exists():current.write_text(json.dumps(before))
            live.bind('mp2650','unbind')
        else:assert driver=='samurai-mp2650',driver
        try:
            load_module(meta,'samurai-mp2650',['runtime_board=1','control=1'])
            assert (live.CLIENT/'driver').resolve().name=='samurai-mp2650'
            assert Path('/sys/module/samurai_mp2650/parameters/control').read_text().strip()=='Y'
            request(psy,'input_current_limit','900000')
            request(psy,'constant_charge_current','250000')
            # AUTO may initially wait for a known native SDP allowance. Its
            # kernel request remains active; source transitions cannot clear
            # a previously latched electrical/IO fault.
            request(psy,'charge_behaviour','auto')
            time.sleep(.2)
            data=sample()
            assert data['shadow']==0 and not data['latched'] and not data['stop_error']
            return {'managed':True,'requested':'auto','waiting_for_source':bool(data['source_inhibit']),'sample':data}
        except BaseException:
            if (live.CLIENT/'driver').resolve().name=='samurai-mp2650':
                try:inhibit(psy)
                except OSError:pass
            elif not (live.CLIENT/'driver').exists():live.bind('mp2650','bind')
            raise
    if action=='stop':
        if driver=='samurai-mp2650':
            inhibit(psy)
        # Keep native providers resident. DWC3 owns the USB supply reference
        # until controller teardown; service stop never removes it.
        return {'managed':driver=='samurai-mp2650','requested':'inhibit-charge'}
    if action=='rollback':
        before=json.loads((STATE/'original-install-private.json').read_text())
        assert driver=='samurai-mp2650'
        inhibit(psy)
        last=t.valid_sample();last['at_monotonic']=time.monotonic()
        last['inherited_ceiling_uv']=3712500+((before['registers']['04'] & 0x7e)>>1)*12500
        live.run('rmmod','samurai_mp2650')
        try:t.rollback(before,last)
        except BaseException:
            try:t.masked(8,8)
            finally:live.bind('mp2650','bind')
            raise
        live.bind('mp2650','bind')
        if Path('/sys/module/samurai_gauge_protection').exists():live.run('rmmod','samurai_gauge_protection')
        retained=Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y'
        if not retained:live.run('rmmod','samurai_usb_input')
        return {'managed':False,'original_configuration_restored':True,'native_input_provider_retained':retained}
    if action=='status':
        return {'managed':driver=='samurai-mp2650','driver':driver,'sample':sample() if driver=='samurai-mp2650' else None}
    raise ValueError(action)

if __name__=='__main__':
    os.umask(0o077)
    assert len(sys.argv)==2
    fd=os.open('/run/lock/samurai-charging.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        assert os.fstat(fd).st_uid==0
        fcntl.flock(fd,fcntl.LOCK_EX)
        data=command(verify(),sys.argv[1])
        tmp=STATE/'state-next-private.json';tmp.write_text(json.dumps(data));tmp.replace(STATE/'state-private.json')
        print(json.dumps(data))
    finally:os.close(fd)
