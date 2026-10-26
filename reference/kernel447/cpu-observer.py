"""Read-only low-rate policy frequency and thermal observations, no CPU policy writes."""
from pathlib import Path
import json,resource,signal,sys,time
running=True
def stop(*_):
 global running
 running=False
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
def read(p):
 try:return p.read_text().strip()
 except OSError:return None
def output(data):print(json.dumps(data,separators=(',',':')),flush=True)
policies=sorted(Path('/sys/devices/system/cpu/cpufreq').glob('policy*'))
thermal=[p for p in Path('/sys/class/thermal').glob('thermal_zone*') if any(s in (read(p/'type') or '').lower() for s in ['cpu','soc'])]
output(dict(kind='configuration',monotonic_ns=time.monotonic_ns(),online=read(Path('/sys/devices/system/cpu/online')),policies={p.name:{n:read(p/n) for n in ['related_cpus','affected_cpus','scaling_governor','scaling_min_freq','scaling_max_freq','cpuinfo_min_freq','cpuinfo_max_freq']} for p in policies},thermal_types={p.name:read(p/'type') for p in thermal}))
samples=0;start=time.monotonic_ns()
while running:
 output(dict(kind='sample',monotonic_ns=time.monotonic_ns(),reported_scaling_khz={p.name:read(p/'scaling_cur_freq') for p in policies},temperatures_millidegrees={p.name:read(p/'temp') for p in thermal} if not samples%5 else {}))
 samples+=1;time.sleep(.1)
usage=resource.getrusage(resource.RUSAGE_SELF)
output(dict(kind='finished',monotonic_ns=time.monotonic_ns(),samples=samples,elapsed_ns=time.monotonic_ns()-start,cpu_seconds=usage.ru_utime+usage.ru_stime))
