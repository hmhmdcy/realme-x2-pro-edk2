from pathlib import Path
import json,os
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k210-runtime/boot-id-private.txt').read_bytes()
rows=[]
for process in Path('/proc').iterdir():
    if not process.name.isdigit():continue
    try:
        for p in (process/'fd').iterdir():
            try:
                target=os.readlink(p)
                if target.startswith(('/dev/video','/dev/media','/dev/v4l-subdev')):rows.append(dict(pid=int(process.name),comm=(process/'comm').read_text().strip(),fd=p.name,target=target,uid=int((process/'status').read_text().split('Uid:',1)[1].split()[0])))
            except OSError:pass
    except OSError:pass
print(json.dumps(dict(stage=210,clients=rows,sensor_pm=Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip(),camss_pm=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip())))
