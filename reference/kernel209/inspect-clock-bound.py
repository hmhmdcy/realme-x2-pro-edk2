from pathlib import Path
import json,math,os,subprocess,time
os.umask(0o077)
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k209-baseline/boot-id-private.txt').read_bytes()
out=root/'k209-clock-inspection';out.mkdir(mode=0o700)
started=time.monotonic()
p=subprocess.run(['chronyc','-n','tracking'],capture_output=True,text=True,timeout=10)
(out/'chrony-tracking-private.txt').write_text(p.stdout+p.stderr)
assert p.returncode==0
fields={line.split(':',1)[0].strip():line.split(':',1)[1].strip() for line in p.stdout.splitlines() if ':' in line}
assert fields['Leap status']=='Normal'
values={name:float(fields[name].split()[0]) for name in ['System time','Root delay','Root dispersion','Skew']}
assert all(math.isfinite(value) for value in values.values()) and values['Root dispersion']>=0
bound=abs(values['System time'])+values['Root dispersion']+max(0,values['Root delay'])/2
report=dict(stage=209,chrony_normal=True,stratum=int(fields['Stratum']),values_seconds_or_skew_ppm=values,chrony_absolute_error_bound_ms=bound*1000,tracking_query_elapsed_ms=(time.monotonic()-started)*1000,manual_clock_or_utc_change=False,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
