"""Stop the exact observed faulting preview and preserve diagnostic logs."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,signal,subprocess,time
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
obs=json.loads((r/'k240-snapshot-observed-stream/summary.json').read_text());assert obs['fault_delta']['gpu']>0
known=json.loads((r/'k240-existing-snapshot/processes-private.json').read_text());apps=[x for x in known if x['comm']=='snapshot'];assert len(apps)==1
out=r/'k240-snapshot-fault-stop';assert not out.exists();out.mkdir(mode=0o700)
app=apps[0];proc=Path('/proc',str(app['pid']));same=proc.exists() and (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==app['start_ticks']
if same:
 assert os.readlink(proc/'exe')=='/usr/bin/snapshot'
 assert int((proc/'status').read_text().split('Uid:',1)[1].split()[0])==10000
 os.kill(app['pid'],signal.SIGTERM)
 deadline=time.monotonic()+10
 while proc.exists() and (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==app['start_ticks'] and time.monotonic()<deadline:time.sleep(.1)
alive=proc.exists() and (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==app['start_ticks']
time.sleep(2)
logs={}
for x in known:
 for path in set(x['log_targets'].values()):
  q=Path(path)
  if q.is_file() and path not in logs:logs[path]=q.read_bytes()[-512*1024:].decode(errors='replace')
(out/'camera-logs-private.json').write_text(json.dumps(logs,indent=2)+'\n')
dmesg=subprocess.check_output(['dmesg'],timeout=5);(out/'dmesg-private.txt').write_bytes(dmesg)
fault_lines=[x for x in dmesg.decode(errors='replace').splitlines() if 'gpu fault:' in x][-30:]
(out/'gpu-fault-lines-private.txt').write_text('\n'.join(fault_lines)+'\n')
media=subprocess.check_output(['media-ctl','-d','/dev/media0','-p'],timeout=6);(out/'media-after-private.txt').write_bytes(media)
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/ac4a000.cci','/sys/bus/platform/devices/ac4b000.cci','/sys/bus/platform/devices/acb3000.camss']
statuses={Path(p).name:Path(p,'power/runtime_status').read_text().strip() for p in devices}
tools={name:bool(list(Path('/usr/bin').glob(name)) or list(Path('/usr/sbin').glob(name))) for name in ['wpctl','pw-cli','pw-dump','gdb','strace','pkg-config']}
report=dict(stage=240,exact_existing_faulting_snapshot_stopped=not alive,sent_SIGTERM=same,forced_kill=False,
 camera_runtime_status=statuses,camera_devices_suspended=all(v=='suspended' for v in statuses.values()),
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),available_tools=tools,no_photo_or_pixel_reads=True,
 total_retained_gpu_fault_lines=len(fault_lines))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/'snapshot-fault-stop-host-private.log').write_bytes(p.stdout+p.stderr)
data=json.loads(p.stdout);(R/'snapshot-fault-stop-validation.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data))
