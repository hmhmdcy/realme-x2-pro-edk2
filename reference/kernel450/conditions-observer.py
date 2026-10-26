"""Bounded read-only observations; check cancellation between sysfs reads."""
from pathlib import Path
import json,resource,signal,time
running=True
def stop(*_):
 global running
 running=False
signal.signal(signal.SIGTERM,stop)
def read(p):
 try:return p.read_text().strip()
 except OSError:return None
def emit(value):print(json.dumps(value,separators=(',',':')),flush=True)
def read_fields(paths):
 result={}
 for name,path in paths:
  if not running:return None
  result[name]=read(path)
 return result if running else None
policies=sorted(Path('/sys/devices/system/cpu/cpufreq').glob('policy*'))
zones={p.name:p for p in Path('/sys/class/thermal').glob('thermal_zone*') if any(s in (read(p/'type') or '').lower() for s in ['cpu','soc','camera','skin','batt'])}
emit(dict(kind='configuration',monotonic_ns=time.monotonic_ns(),thermal_types={n:read(p/'type') for n,p in zones.items()},policies={p.name:{n:read(p/n) for n in ['related_cpus','scaling_governor','scaling_min_freq','scaling_max_freq']} for p in policies}))
started=time.monotonic_ns();samples=0
while running:
 stamp=time.monotonic_ns()
 temperatures=read_fields((n,p/'temp') for n,p in zones.items())
 if temperatures is None:break
 frequencies=read_fields((p.name,p/'scaling_cur_freq') for p in policies)
 if frequencies is None:break
 telemetry=read(Path('/sys/bus/i2c/devices/0-005c/telemetry'))
 if not running:break
 emit(dict(kind='sample',monotonic_ns=stamp,temperatures_millidegrees=temperatures,reported_scaling_khz=frequencies,charging_telemetry=telemetry))
 samples+=1
 if running:time.sleep(1)
u=resource.getrusage(resource.RUSAGE_SELF);emit(dict(kind='finished',monotonic_ns=time.monotonic_ns(),samples=samples,elapsed_ns=time.monotonic_ns()-started,cpu_seconds=u.ru_utime+u.ru_stime))
