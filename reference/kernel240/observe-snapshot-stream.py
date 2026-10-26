"""Trace metadata only for an existing preview; never open or stop the app."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,re,subprocess,time,traceback
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
prior=json.loads((r/'k240-existing-snapshot/processes-private.json').read_text());apps=[x for x in prior if x['comm']=='snapshot'];assert len(apps)==1
app=apps[0];proc=Path('/proc',str(app['pid']));assert (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==app['start_ticks']
out=r/'k240-snapshot-observed-stream';assert not out.exists();out.mkdir(mode=0o700)
before=subprocess.check_output(['dmesg'],timeout=5)
(out/'dmesg-before-private.txt').write_bytes(before)
trace=Path('/sys/kernel/tracing/instances/k240_snapshot_observed');assert not trace.exists();trace.mkdir()
error=None;raw='';stats={};cleanup=[];start=time.monotonic()
try:
 (trace/'tracing_on').write_text('0');(trace/'events/enable').write_text('0');(trace/'buffer_size_kb').write_text('512');(trace/'trace_clock').write_text('mono')
 for name in ['vb2_v4l2_buf_done','vb2_v4l2_dqbuf']:
  event=trace/'events/v4l2'/name
  assert 'field:int minor;' in (event/'format').read_text()
  (event/'filter').write_text('minor == 0');assert 'parse_error' not in (event/'filter').read_text()
  (event/'enable').write_text('1')
 (trace/'tracing_on').write_text('1');time.sleep(5);(trace/'tracing_on').write_text('0')
 raw=(trace/'trace').read_text()
 (out/'video-buffer-trace-private.txt').write_text(raw)
 for p in trace.glob('per_cpu/cpu*/stats'):stats[p.parent.name]=p.read_text()
except BaseException:error=traceback.format_exc();(out/'failure-private.txt').write_text(error)
finally:
 for leaf in ['tracing_on','events/enable']:
  try:(trace/leaf).write_text('0')
  except OSError as e:cleanup.append(str(e))
 try:trace.rmdir()
 except OSError as e:cleanup.append(str(e))
(out/'trace-stats-private.json').write_text(json.dumps(stats,indent=2)+'\n')
events=[]
for line in raw.splitlines():
 m=re.search(r'\s(\d+\.\d+): (vb2_v4l2_(?:buf_done|dqbuf)): (.*)',line)
 if m:
  text=m[3];seq=re.search(r'sequence = (\d+)',text);ts=re.search(r'timestamp = (\d+)',text)
  events.append(dict(event=m[2],trace_seconds=float(m[1]),sequence=int(seq[1]),timestamp_ns=int(ts[1]),error='|ERROR|' in text or 'flags = ERROR|' in text))
(out/'buffer-metadata-private.json').write_text(json.dumps(events,indent=2)+'\n')
counts={}
for name in ['vb2_v4l2_buf_done','vb2_v4l2_dqbuf']:
 e=[x for x in events if x['event']==name];seq=[x['sequence'] for x in e]
 counts[name]=dict(count=len(e),unique_sequences=len(set(seq)),first_sequence=seq[0] if seq else None,last_sequence=seq[-1] if seq else None,
  timestamps_strictly_increasing=bool(e) and all(b['timestamp_ns']>a['timestamp_ns'] for a,b in zip(e,e[1:])),error_frames=sum(x['error'] for x in e))
data={}
for label,args in [('capture-format',['v4l2-ctl','-d','/dev/video0','--get-fmt-video']),('front-controls',['v4l2-ctl','-d','/dev/v4l-subdev15','--get-ctrl=exposure,analogue_gain,digital_gain,vertical_blanking'])]:
 p=subprocess.run(args,capture_output=True,timeout=5);data[label]=dict(exit=p.returncode,stdout=p.stdout.decode(errors='replace'),stderr=p.stderr.decode(errors='replace'))
(out/'read-only-video-state-private.json').write_text(json.dumps(data,indent=2)+'\n')
logs={}
for x in prior:
 for path in set(x['log_targets'].values()):
  q=Path(path)
  if not q.is_file() or path in logs:continue
  logs[path]=q.read_bytes()[-256*1024:].decode(errors='replace')
(out/'session-camera-logs-private.json').write_text(json.dumps(logs,indent=2)+'\n')
after=subprocess.check_output(['dmesg'],timeout=5);(out/'dmesg-after-private.txt').write_bytes(after)
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received').items()}
alive=proc.exists() and (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==app['start_ticks']
report=dict(stage=240,observed_existing_snapshot=True,no_new_application_or_capture_requested=True,no_shutter_or_pixel_reads=True,
 observed_seconds=round(time.monotonic()-start,3),buffer_events=counts,application_still_alive=alive,trace_removed=not trace.exists(),trace_cleanup_errors=cleanup,
 trace_failure=bool(error),sensor_runtime_status={b:Path('/sys/bus/i2c/devices',b,'power/runtime_status').read_text().strip() for b in ['7-0010','9-0010']},
 fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),read_only_video_state=data)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
assert not error and not cleanup and not any(faults.values())
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/'snapshot-observed-host-private.log').write_bytes(p.stdout+p.stderr)
data=json.loads(p.stdout)
(R/'snapshot-existing-stream-validation.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data))
