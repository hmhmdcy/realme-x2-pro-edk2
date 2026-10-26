"""Bounded normal CPU work. Exits on parent loss, stale control or charger stop."""
from pathlib import Path
import ctypes,hashlib,json,os,signal,sys,time
cpu,parent,deadline=int(sys.argv[1]),int(sys.argv[2]),float(sys.argv[3])
HERE=Path(__file__).resolve().parent
assert cpu in (4,7)
assert ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGTERM,0,0,0)==0
assert os.getppid()==parent
os.sched_setaffinity(0,{cpu})
data=b'normal CPU work during unchanged AUTO timer observation\0'*2048
while time.clock_gettime(time.CLOCK_BOOTTIME)<deadline:
    if os.getppid()!=parent:break
    if '[auto]' not in Path('/sys/class/power_supply/mp2650-input/charge_behaviour').read_text():break
    sample={k:int(v) for k,v in (x.split('=',1) for x in Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text().split())}
    if any(sample[k] for k in ['cycle_timeout','latched','error','stop_error','fault','thermal_inhibit','source_inhibit']):break
    if not sample['desired_enable'] or sample['valid']!=1 or sample['online']!=1 or sample['protection_ok']!=1:break
    control=json.loads((HERE/'cpu-load-control.json').read_bytes())
    duty=control['duty'];age=time.clock_gettime(time.CLOCK_BOOTTIME)-control['boottime']
    if not 0<=age<30:break
    assert type(duty) in (int,float) and 0<=duty<=0.3
    start=time.monotonic();busy_until=start+0.2*duty
    while time.monotonic()<busy_until:hashlib.sha256(data).digest()
    time.sleep(max(0,start+0.2-time.monotonic()))
