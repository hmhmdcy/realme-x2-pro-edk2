"""One RTC-backed s2idle check of installed charging callbacks and resume.

No driver rebinds, charger property writes, USB role changes or service stops.
Normal kernel PM invokes the installed driver's stop/resample paths.
"""
from pathlib import Path
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import traceback

os.umask(0o077)
ROOT=Path('/root/charging-management-20261023')
out=ROOT/'charging-pm';assert not out.exists();out.mkdir(mode=0o700)
spec=importlib.util.spec_from_file_location('live',ROOT/'live-session.py')
live=importlib.util.module_from_spec(spec);spec.loader.exec_module(live)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==Path('/var/lib/samurai/charging-usb-dt/boot-id-private.txt').read_bytes()
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k363+'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/power/mem_sleep').read_text().strip()=='[s2idle]'
assert (live.CLIENT/'driver').resolve().name=='samurai-mp2650'
assert all((Path('/sys/bus/platform/devices')/n/'power/runtime_status').read_text().strip()=='suspended'
    for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci'])
assert not json.loads(Path('/var/lib/samurai/gnss-assist/watch-state.json').read_text())['active']
for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'):assert p.read_text().strip()=='closed'
for addr in ['1-0039','1-003a']:assert 'powered=0 muted=1' in Path('/sys/bus/i2c/devices',addr,'status').read_text()
alarm=Path('/sys/class/rtc/rtc0/wakealarm')
assert not alarm.read_text().strip()
assert Path('/sys/class/rtc/rtc0/device/power/wakeup').read_text().strip()=='enabled'

def write_json(name,data):
    p=out/(name+'.json');tmp=p.with_suffix('.next');tmp.write_text(json.dumps(data));tmp.replace(p)

def phase(name,**fields):write_json('phase-private',{'phase':name,'pid':os.getpid(),**fields})

def irq():
    line=next(x for x in Path('/proc/interrupts').read_text().splitlines() if x.endswith('pm8xxx_rtc_alarm'))
    return sum(int(x) for x in line.split()[1:9])

def stats():return {p.name:p.read_text().strip() for p in Path('/sys/power/suspend_stats').iterdir() if p.is_file()}

def telemetry():return {k:int(v) for k,v in (x.split('=') for x in (live.CLIENT/'telemetry').read_text().split())}

def allowance():
    try:return {'ua':int((live.PSY/'samurai-usb-input/input_current_limit').read_text())}
    except OSError as e:return {'errno':e.errno}

before=live.state();first=telemetry()
assert first['valid']==first['protection_ok']==first['desired_enable']==1 and not first['error']
write_json('before-private',before);write_json('sample-before-private',first)
write_json('native-allowance-before-private',allowance())
trace=Path('/sys/kernel/tracing/instances/charging-pm-20261023')
target=None;trace_saved=False
events=['suspend_resume','device_pm_callback_start','device_pm_callback_end']
try:
    phase('rtc-preflight')
    count=irq();target=int(Path('/sys/class/rtc/rtc0/since_epoch').read_text())+5
    started=time.monotonic();alarm.write_text(str(target))
    while irq()==count and time.monotonic()-started<10:time.sleep(.1)
    assert irq()-count==1 and 3<=time.monotonic()-started<=7
    assert not alarm.read_text().strip();target=None
    trace.mkdir();(trace/'buffer_size_kb').write_text('512')
    for name in events:(trace/'events/power'/name/'enable').write_text('1')
    (trace/'tracing_on').write_text('1')
    initial=stats();before_log=subprocess.check_output(['dmesg'],text=True);count=irq()
    write_json('suspend-stats-before-private',initial);(out/'dmesg-before-private.txt').write_text(before_log)
    target=int(Path('/sys/class/rtc/rtc0/since_epoch').read_text())+15
    alarm.write_text(str(target));assert alarm.read_text().strip()==str(target)
    phase('armed-before-suspend',alarm_delay_seconds=15)
    os.sync();mono=time.monotonic();bt=time.clock_gettime(time.CLOCK_BOOTTIME)
    try:Path('/sys/power/state').write_text('mem');result={'errno':0}
    except OSError as e:result={'errno':e.errno,'message':str(e)}
    elapsed=time.monotonic()-mono;boot_elapsed=time.clock_gettime(time.CLOCK_BOOTTIME)-bt
    phase('returned-from-suspend',result=result)
    (trace/'tracing_on').write_text('0')
    (out/'pm-trace-private.txt').write_text((trace/'trace').read_text());trace_saved=True
    time.sleep(3)
    after=live.state();last=telemetry();final=stats();log=subprocess.check_output(['dmesg'],text=True)
    write_json('after-private',after);write_json('sample-after-private',last)
    write_json('native-allowance-after-private',allowance());write_json('suspend-stats-after-private',final)
    (out/'dmesg-after-private.txt').write_text(log)
    delta={k:int(final[k])-int(initial[k]) for k in initial if re.fullmatch(r'\d+',initial[k]) and re.fullmatch(r'\d+',final[k])}
    faults={x:log.count(x)-before_log.count(x) for x in ['WARNING:','Oops:','refcount_t: underflow','gpu fault:','NGD resume failed']}
    same=before['camera_pm']==after['camera_pm'] and before['m2m']==after['m2m'] and before['services']==after['services']
    healthy=(last['valid']==last['online']==last['protection_ok']==last['desired_enable']==1 and
        not any(last[k] for k in ['error','stop_error','latched','source_inhibit','fault']) and last['age_ms']<2000)
    report={'terminal':True,'sysfs_result':result,'same_boot':boot==Path('/proc/sys/kernel/random/boot_id').read_bytes(),
        'suspend_stats_delta':delta,'rtc_irq_delta':irq()-count,'residency_seconds':boot_elapsed-elapsed,
        'boottime_seconds':boot_elapsed,'monotonic_seconds':elapsed,'taint':int(after['taint']),
        'fault_delta':faults,'camera_and_four_services_unchanged':same,'charging_resumed_healthy':healthy,
        'native_allowance_after':allowance(),'trace_audit_pending':True}
    report['runtime_passed']=bool(result['errno']==0 and delta.get('success')==1 and not delta.get('fail',0)
        and report['same_boot'] and report['taint']==0 and not any(faults.values()) and same and healthy)
    write_json('runtime-result',report);phase('terminal',passed=report['runtime_passed'])
    print(json.dumps(report),flush=True)
except BaseException:
    (out/'failure-private.txt').write_text(traceback.format_exc());phase('failed',terminal=True)
    raise
finally:
    if target is not None and alarm.read_text().strip()==str(target):alarm.write_text('0')
    if trace.exists():
        (trace/'tracing_on').write_text('0')
        if not trace_saved:(out/'pm-trace-private.txt').write_text((trace/'trace').read_text())
        for name in events:(trace/'events/power'/name/'enable').write_text('0')
        trace.rmdir()
