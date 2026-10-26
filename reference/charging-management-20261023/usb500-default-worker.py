"""One detached normal-startup invocation; no retry and no implicit rollback."""
from pathlib import Path
import fcntl, hashlib, json, os, subprocess, sys, time, traceback

ROOT = Path('/var/lib/samurai/usb500-default-r1')
SCRIPT = Path('/usr/local/sbin/samurai-usb')
GADGET = Path('/sys/kernel/config/usb_gadget/samurai')
PS = Path('/sys/class/power_supply')
sha = lambda b: hashlib.sha256(b).hexdigest()

def save(name, value):
    tmp = ROOT / (name + '.next')
    with tmp.open('w') as f:
        json.dump(value, f, indent=2); f.flush(); os.fsync(f.fileno())
    tmp.replace(ROOT/name)

def snapshot():
    telemetry = {k:int(v) for k,v in (x.split('=') for x in
                 Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text().split())}
    source = {k:(PS/'samurai-usb-input'/k).read_text().strip() for k in
              ['online','usb_type','current_max','input_current_limit']}
    charger = {k:int((PS/'mp2650-input'/k).read_text()) for k in
               ['input_current_limit','constant_charge_current','constant_charge_voltage']}
    return dict(telemetry=telemetry, source=source, charger=charger,
                MaxPower_ma=int((GADGET/'configs/c.1/MaxPower').read_text()),
                binding=(GADGET/'UDC').read_text().strip(),
                udc=Path('/sys/class/udc/a600000.usb/state').read_text().strip(),
                boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME))

def healthy(r, ma):
    t,s,c=r['telemetry'],r['source'],r['charger']
    assert t['valid']==t['online']==t['protection_ok']==t['desired_enable']==1
    assert 0<=t['age_ms']<=3000
    assert all(t[k]==0 for k in ['shadow','error','stop_error','latched','fault',
               'source_inhibit','thermal_inhibit','cycle_timeout','gauge_charge_stop'])
    assert r['MaxPower_ma']==ma and r['binding']=='a600000.usb' and r['udc']=='configured'
    assert s['online']=='1' and '[SDP]' in s['usb_type']
    assert int(s['current_max'])==int(s['input_current_limit'])==t['budget_ua']==ma*1000
    assert c=={'input_current_limit':ma*1000,'constant_charge_current':250000,
               'constant_charge_voltage':8725000}
    assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'

def main():
    assert os.geteuid()==0 and not sys.flags.optimize
    request=json.loads((ROOT/'request-private.json').read_bytes())
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    assert boot==request['expected_boot']==Path(request['guard']).read_text().strip()
    assert sha(SCRIPT.read_bytes())==request['new_sha256']
    assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())==request['manifest_sha256']
    assert not Path('/run/samurai-dropbear.pid').exists()
    assert not Path('/run/samurai-usb.lock').exists()
    fd=os.open('/run/lock/samurai-charging.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    state={'phase':'preflight','pid':os.getpid(),'terminal':False,'passed':False,
           'startup_invocations':0,'budget_direct_writes':0}
    save('activation-state-private.json',state)
    try:
        before=snapshot();healthy(before,100);save('before-private.json',before)
        # Let the launch receipt reach the host before the known USB disconnect.
        time.sleep(1)
        with (ROOT/'startup-private.log').open('xb') as log:
            state.update(phase='normal-startup-intent',startup_invocations=1)
            save('activation-state-private.json',state)
            child=subprocess.Popen([str(SCRIPT),'start'],stdin=subprocess.DEVNULL,
                stdout=log,stderr=subprocess.STDOUT,close_fds=True)
            state['child_pid']=child.pid
            try:
                st=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()
                state.update(phase='normal-startup-running',child_pid=child.pid,
                             child_startticks=int(st[19]))
                save('activation-state-private.json',state)
            finally:
                # A receipt error must not abandon a live startup or release its lock.
                # Wait for this exact child; never kill it or invoke startup again.
                while True:
                    try:
                        rc=child.wait()
                        break
                    except (KeyboardInterrupt,InterruptedError):
                        continue
                state.update(child_terminal=True,child_returncode=rc)
        state.update(child_terminal=True,child_returncode=rc,phase='checking-native500')
        save('activation-state-private.json',state)
        assert rc==0,'normal startup failed; inspect exact child/state, do not replay'
        samples=[];since=None;deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            r=snapshot();samples.append(r)
            try: healthy(r,500)
            except (AssertionError,OSError): since=None
            else:
                if since is None: since=time.monotonic()
                if time.monotonic()-since>=3: break
            time.sleep(.5)
        else: raise RuntimeError('native500 was not continuously healthy; no implicit rollback')
        save('samples-private.json',samples)
        assert sha(SCRIPT.read_bytes())==request['new_sha256']
        state.update(phase='native500-active',terminal=True,passed=True,
                     final=samples[-1],startup_default_ma=500)
        save('activation-state-private.json',state)
    except BaseException:
        state.update(phase='failed-inspect-before-next-action',terminal=True,
                     error=traceback.format_exc())
        save('activation-state-private.json',state)
        raise
    finally:
        os.close(fd)

if __name__=='__main__': main()
