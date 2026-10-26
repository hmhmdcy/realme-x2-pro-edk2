"""One PM freezer-only experiment; preserve early measurements even on DSP failure."""
from pathlib import Path
import argparse,json,os,re,subprocess,time

parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
os.umask(0o077);out=Path(args.output);assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189-reboot-runtime/boot-id-private.txt').read_bytes()
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip()=='running'
pm=Path('/sys/power/pm_test');original=re.search(r'\[([^]]+)\]',pm.read_text())[1];assert original=='none'
debug=Path('/sys/kernel/debug/dynamic_debug/control')
rows=[line for line in debug.read_text().splitlines() if 'fastrpc_internal_invoke ' in line]
assert rows and all('p' not in re.search(r'\s=([^ ]*) ',line)[1] for line in rows)
(out/'dynamic-debug-before-private.txt').write_text('\n'.join(rows)+'\n')
trace=Path('/sys/kernel/tracing/instances/k189-freezer-case');assert not trace.exists();trace.mkdir()
events=['suspend_resume','device_pm_callback_start','device_pm_callback_end']
log_before=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-before-private.txt').write_text(log_before)
env=dict(os.environ,LD_LIBRARY_PATH='/var/lib/samurai/k184-libssc-r2/build-r4/src',LIBSSC_LIGHT_DATA_TYPE='wise_light')
def stream(label):
 p=subprocess.run(['ssccli','--debug','--sensor','accelerometer','--timeout','2'],capture_output=True,env=env,timeout=20)
 raw=(p.stdout+p.stderr).decode(errors='replace');(out/(label+'-accel-private.txt')).write_bytes(p.stdout+p.stderr)
 return dict(exit=p.returncode,samples=raw.count('Accelerometer sensor measurement:'),disabled='accelerometer sensor disabled' in raw.lower())
report=dict(stage=189,pm_test='freezer',kernel_build=183,mem_writes_requested=0)
try:
 report['before']=stream('before');assert report['before']['exit']==0 and report['before']['samples']>0
 debug.write_text('func fastrpc_internal_invoke +p')
 (trace/'buffer_size_kb').write_text('512')
 for name in events:(trace/'events/power'/name/'enable').write_text('1')
 (trace/'tracing_on').write_text('1')
 pm.write_text('freezer');assert '[freezer]' in pm.read_text()
 report['mem_writes_requested']=1
 with (out/'phase-private.json').open('w') as f:
  json.dump(dict(phase='armed',mem_writes_requested=1),f);f.flush();os.fsync(f.fileno())
 start=time.monotonic()
 try:Path('/sys/power/state').write_text('mem');errno=0
 except OSError as e:errno=e.errno
 report.update(sysfs_errno=errno,freezer_test_elapsed_seconds=time.monotonic()-start)
 (out/'phase-private.json').write_text(json.dumps(dict(phase='returned',**report)))
 time.sleep(2)
 report['slpi_state_after']=Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip()
 if report['slpi_state_after']=='running':report['after']=stream('after')
 else:report['after']=dict(not_run='SLPI not running')
 report['slpi_state_final']=Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip()
finally:
 pm.write_text(original)
 debug.write_text('func fastrpc_internal_invoke -p')
 after_rows=[line for line in debug.read_text().splitlines() if 'fastrpc_internal_invoke ' in line]
 (out/'dynamic-debug-after-private.txt').write_text('\n'.join(after_rows)+'\n')
 report['dynamic_debug_restored']=rows==after_rows
 report['pm_test_restored']='['+original+']' in pm.read_text()
 (trace/'tracing_on').write_text('0')
 data=(trace/'trace').read_text();(out/'power-trace-private.txt').write_text(data)
 stats={p.parent.name:p.read_text() for p in (trace/'per_cpu').glob('cpu*/stats')}
 (out/'trace-stats-private.json').write_text(json.dumps(stats,indent=2))
 for name in events:(trace/'events/power'/name/'enable').write_text('0')
 trace.rmdir()
 after=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-after-private.txt').write_text(after)
 assert after.startswith(log_before);extra=after[len(log_before):]
 report.update(fault_delta={key:extra.count(value) for key,value in dict(warning='WARNING:',oops='Oops:',
  slpi_fatal='fatal error received',slpi_crash='crash detected in slpi',scm='Assign memory protection call failed',
  invoke_interrupted='Error: Invoke Failed -512').items()},taint=int(Path('/proc/sys/kernel/tainted').read_text()),
  power=Path('/sys/devices/platform/sensor-power/state').read_text().strip(),
  device_pm_callback_events=data.count('device_pm_callback_end:'),
  machine_suspend_events=data.count('machine_suspend['),trace_cpu_count=len(stats),
  trace_overrun_total=sum(int(re.search(r'^overrun:\s*(\d+)',s,re.M)[1]) for s in stats.values()))
 report['sensor_survived_freezer']=bool(report.get('sysfs_errno')==0 and report.get('slpi_state_final')=='running'
  and report.get('after',{}).get('samples',0)>0 and report['after']['exit']==0 and report['after']['disabled']
  and not report['fault_delta']['slpi_fatal'] and report['taint']==0)
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
assert report['dynamic_debug_restored'] and report['pm_test_restored']
raise SystemExit(0 if report['sensor_survived_freezer'] else 1)
