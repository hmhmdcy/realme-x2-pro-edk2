"""Briefly pause the verified idle desktop camera monitor, then always resume."""
from pathlib import Path
import json,os,signal,time
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k210-runtime/boot-id-private.txt').read_bytes()
clients=[]
for process in Path('/proc').iterdir():
    if not process.name.isdigit():continue
    try:
        for p in (process/'fd').iterdir():
            try:
                if os.readlink(p).startswith(('/dev/video','/dev/media','/dev/v4l-subdev')):clients.append((int(process.name),p.name,os.readlink(p)))
            except OSError:pass
    except OSError:pass
pids={p[0] for p in clients};assert len(pids)==1
pid=next(iter(pids));proc=Path('/proc')/str(pid)
assert (proc/'comm').read_text().strip()=='wireplumber'
assert int((proc/'status').read_text().split('Uid:',1)[1].split()[0])==10000
assert Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip()=='suspended'
assert Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip()=='suspended'
start=(proc/'stat').read_text().split()[21]
status=(proc/'status').read_text();assert 'State:\tT' not in status
source=(root/'k210-capture-tools/capture-static-front.py').read_text()
source=source.replace("root/'k210-static-front-capture'","root/'k210-static-front-capture-r2'")
old="if target.startswith(('/dev/video','/dev/media','/dev/v4l-subdev')):result.append"
assert source.count(old)==1
source=source.replace(old,"if process.name!='"+str(pid)+"' and target.startswith(('/dev/video','/dev/media','/dev/v4l-subdev')):result.append")
fixture=root/'k210-capture-monitor-fixture';fixture.mkdir(mode=0o700)
record=dict(stage=210,only_idle_wireplumber_holds_camera_fds=True,monitored_camera_fds=len(clients),monitor_paused=False,monitor_resumed=False,first_capture_guard_stopped_before_stream_due_to_monitor_fds=True)
def save():(fixture/'summary.json').write_text(json.dumps(record,indent=2)+'\n')
save()
try:
    os.kill(pid,signal.SIGSTOP)
    for _ in range(50):
        if 'State:\tT' in (proc/'status').read_text():break
        time.sleep(.01)
    assert 'State:\tT' in (proc/'status').read_text();record['monitor_paused']=True;save()
    exec(compile(source,'capture-with-idle-monitor-paused','exec'),{'__name__':'__main__'})
finally:
    assert (proc/'stat').read_text().split()[21]==start and (proc/'comm').read_text().strip()=='wireplumber'
    os.kill(pid,signal.SIGCONT);time.sleep(.1)
    assert 'State:\tT' not in (proc/'status').read_text()
    record['monitor_resumed']=True;save()
