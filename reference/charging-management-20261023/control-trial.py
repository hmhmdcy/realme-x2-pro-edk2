"""Bounded ordinary charging trial with fresh-source checked rollback.

Manual worker only, inside a separately coordinated phone window. Does not
install a boot service, program protection devices or change USB/camera state.
"""
from pathlib import Path
import ctypes as C
import errno
import importlib.util
import json
import os
import signal
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('live',ROOT/'live-session.py')
live=importlib.util.module_from_spec(spec);spec.loader.exec_module(live)
OUT=ROOT/'control-trial'
MASKS={0x00:0x7f,0x0f:0x7f,0x02:0x7f,0x03:0xff,0x04:0x7f,0x08:0x18}

def save(name,data):
    p=OUT/(name+'.json');tmp=p.with_suffix('.next');tmp.write_text(json.dumps(data));tmp.replace(p)

def sample():
    text=(live.CLIENT/'telemetry').read_text()
    return {k:int(v) for k,v in (item.split('=') for item in text.split())}

def valid_sample():
    d=sample()
    assert d['valid']==d['online']==d['protection_ok']==1 and d['shadow']==0
    assert not any(d[k] for k in ['error','stop_error','latched','fault'])
    assert d['age_ms']<2000 and 160<=d['temp_decic']<440
    assert 4000000<=d['cell1_uv']<=4410000 and 4000000<=d['cell2_uv']<=4410000
    return d

def prop(name): return live.PSY/'mp2650-input'/name
def setprop(name,value): prop(name).write_text(str(value))

def masked(reg,value):
    """Restore only owned fields after the managed writer has been removed."""
    assert not Path('/sys/module/samurai_mp2650').exists()
    assert not (live.CLIENT/'driver').exists()
    mask=MASKS[reg]
    old=live.registers()[f'{reg:02x}']
    if reg==8: assert old & 0xc0 == 0
    new=(old & ~mask)|(value & mask)
    if new != old:
        fd=os.open('/dev/i2c-0',os.O_RDWR|os.O_CLOEXEC)
        try:
            buf=C.create_string_buffer(bytes([reg,new]))
            msgs=(live.Msg*1)(live.Msg(0x5c,0,2,C.cast(buf,C.c_void_p)))
            libc=C.CDLL(None,use_errno=True)
            ret=libc.ioctl(fd,0x0707,C.byref(live.Transfer(msgs,1)))
            if ret!=1: raise OSError(C.get_errno() if ret<0 else errno.EIO,'restore charger field')
        finally: os.close(fd)
    assert live.registers()[f'{reg:02x}']==new

def rollback(before,last):
    # Stop first. Never re-enable after missing/error/stale telemetry or a
    # source whose present allowance is smaller than the original settings.
    masked(8,8)
    ps=live.PSY
    assert int((ps/'samurai-usb-input/online').read_text())==1
    budget=int((ps/'samurai-usb-input/current_max').read_text())
    assert int((ps/'samurai-gauge-protection/present').read_text())==1
    assert (ps/'samurai-gauge-protection/health').read_text().strip()=='Good'
    assert last and time.monotonic()-last['at_monotonic']<5
    assert 160<=last['temp_decic']<440 and max(last['cell1_uv'],last['cell2_uv'])<=4410000
    # Recheck fresh temperature through the established battery interface.
    assert 160<=int((ps/'bq28z610-0/temp').read_text())<440
    regs=before['registers'];now=live.registers()
    assert now['13'] & 2
    assert all(now[k]==regs[k] for k in ['01','05','07','09'])
    assert regs['08'] & 0xe0 == 0 and regs['08'] & 6 == 6
    assert regs['09'] & 0x30 == 0 and regs['09'] & 0x48 == 0x48
    assert max(regs['00'] & 0x7f,regs['0f'] & 0x7f)*50000<=min(budget,2000000)
    assert 200000<=(regs['02'] & 0x7f)*50000<=1100000
    assert 3712500+((regs['04'] & 0x7e)>>1)*12500<=min(4400000,last['inherited_ceiling_uv'])
    for reg in [0x0f,0x00,0x02,0x03,0x04]: masked(reg,regs[f'{reg:02x}'])
    masked(8,regs['08'])
    assert live.configuration({'registers':live.registers()})==live.configuration(before)

def trial():
    live.guard()
    assert not OUT.exists();OUT.mkdir(mode=0o700)
    before=live.state();assert before['driver']=='mp2650'
    save('before-private',before)
    state={'pid':os.getpid(),'phase':'starting','terminal':False,'passed':False}
    save('state-private',state)
    changed=False;last=None;primary=None;restore=None;records=[]
    def interrupted(sig,frame): raise RuntimeError('interrupted '+str(sig))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    try:
        assert not any(Path('/sys/module',n).exists() for n in
            ['samurai_usb_input','samurai_gauge_protection','samurai_mp2650'])
        live.run('insmod',str(ROOT/'samurai-usb-input.ko'),'register_board=1')
        live.run('insmod',str(ROOT/'samurai-gauge-protection.ko'),'register_board=1')
        live.bind('mp2650','unbind');changed=True
        live.run('insmod',str(ROOT/'samurai-mp2650.ko'),'runtime_board=1','control=1')
        assert (live.CLIENT/'driver').resolve().name=='samurai-mp2650'
        state['phase']='initial-inhibit';save('state-private',state)
        time.sleep(2)
        first=valid_sample()
        assert live.registers()['08'] & 0x18 == 8
        assert first['budget_ua']>=900000
        setprop('input_current_limit',900000)
        setprop('constant_charge_current',300000)
        setprop('charge_behaviour','auto')
        state['phase']='900mA-input-300mA-charge';save('state-private',state)
        for i in range(3):
            time.sleep(3)
            last=valid_sample();assert last['desired_enable']==1
            last['at_monotonic']=time.monotonic()
            last['inherited_ceiling_uv']=3712500+((before['registers']['04'] & 0x7e)>>1)*12500
            r=live.registers()
            assert r['00'] & 0x7f == 18 and r['0f'] & 0x7f == 18 and r['02'] & 0x7f == 6
            assert r['08'] & 0x18 == 0x10
            records.append({'phase':'900/300','sample':last,'registers':r,
                'battery_current_ua':int((live.PSY/'bq28z610-0/current_now').read_text()),
                'status':prop('status').read_text().strip()})
        setprop('input_current_limit',500000)
        last=valid_sample();last['at_monotonic']=time.monotonic()
        last['inherited_ceiling_uv']=records[-1]['sample']['inherited_ceiling_uv']
        r=live.registers();assert r['00'] & 0x7f == r['0f'] & 0x7f == 10
        records.append({'phase':'500/300','sample':last,'registers':r})
        # Reject a higher-than-OEM request without touching live configuration.
        prior=live.configuration({'registers':r})
        try: setprop('input_current_limit',2000001)
        except OSError as e: assert e.errno==errno.ERANGE
        else: raise AssertionError('invalid input cap accepted')
        assert prior==live.configuration({'registers':live.registers()})
        setprop('charge_behaviour','inhibit-charge')
        assert live.registers()['08'] & 0x18 == 8
        records.append({'phase':'inhibited','sample':sample(),'registers':live.registers()})
        save('observations-private',records)
        state['phase']='rolling-back';save('state-private',state)
    except BaseException:
        primary=traceback.format_exc();save('failure-private',{'traceback':primary})
    finally:
        try:
            if Path('/sys/module/samurai_mp2650').exists():
                # Get a last fresh safety sample immediately before removal.
                if (live.CLIENT/'driver').exists():
                    setprop('charge_behaviour','inhibit-charge')
                    d=valid_sample();d['at_monotonic']=time.monotonic()
                    d['inherited_ceiling_uv']=3712500+((before['registers']['04'] & 0x7e)>>1)*12500
                    last=d
                live.run('rmmod','samurai_mp2650')
            if changed:
                rollback(before,last)
                live.bind('mp2650','bind')
        except BaseException:
            restore=traceback.format_exc();save('rollback-failure-private',{'traceback':restore})
            # Leave normal charging paused on policy/rollback uncertainty.
            if not Path('/sys/module/samurai_mp2650').exists() and not (live.CLIENT/'driver').exists():
                try: masked(8,8);live.bind('mp2650','bind')
                except BaseException: pass
        for n in ['samurai_gauge_protection','samurai_usb_input']:
            if Path('/sys/module',n).exists():
                try: live.run('rmmod',n)
                except BaseException:
                    restore=(restore or '')+traceback.format_exc()
        after=live.state();save('after-private',after)
        same=live.configuration(after)==live.configuration(before)
        unchanged=(after['camera_pm']==before['camera_pm'] and after['m2m']==before['m2m'] and after['services']==before['services'])
        passed=not primary and not restore and same and unchanged and after['taint']=='0'
        state.update(terminal=True,phase='terminal',passed=passed,rollback_configuration_exact=same,
            camera_services_unchanged=unchanged,taint=int(after['taint']),
            positive_battery_current_observed=any(x.get('battery_current_ua',0)>0 for x in records))
        save('state-private',state)
    print(json.dumps(state))
    return 0 if state['passed'] else 1

if __name__=='__main__': sys.exit(trial())
