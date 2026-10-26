from pathlib import Path
import json
import host
code=b'''from pathlib import Path
import dbus,json
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
bus=dbus.SystemBus(private=True);sensor=dbus.Interface(bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties').GetAll('net.hadess.SensorProxy')
has={str(k):bool(v) for k,v in sensor.items() if k in ['HasAccelerometer','HasAmbientLight','HasProximity']};bus.close()
count=0
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if (p/'exe').resolve()==Path('/usr/libexec/samurai-hexagonrpcd'):count+=1
 except FileNotFoundError:pass
report=dict(stage=191,same_boot_as189=True,ssc_file_service_processes=count,sensor_proxy=has)
assert count==1 and all(has.values());print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code);report=json.loads(p.stdout)
(Path(__file__).resolve().parent/'services-after-radio-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
