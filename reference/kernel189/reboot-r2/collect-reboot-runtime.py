from pathlib import Path
import subprocess
import host

ref=Path(__file__).resolve().parent
data=(ref.parents[1]/'kernel185/collect-reboot-runtime.py').read_text()
data=data.replace('k185-reboot-runtime','k189r2-reboot-runtime').replace('k185-preflash','k189r2-preflash').replace("'stage': 185","'stage': 189")
data=data.replace("'slpi': 'offline'","'slpi': 'running'").replace("== 'vdd=0 vddio=0'","== 'vdd=1 vddio=1'")
data=data.replace("'module_overrides': 1","'module_overrides': 2")
# Preserve the independently captured UART failure; it is not a sensor success.
data=data.replace('assert not any(faults.values())',"assert not any(v for k,v in faults.items() if k != 'bluetooth_reassembly')\nassert faults['bluetooth_reassembly'] == 1")
marker="report = {'stage': 189"
extension="""
fastrpc_raw=(module_root/'kernel/drivers/misc/fastrpc.ko').read_bytes()
assert hashlib.sha256(fastrpc_raw).hexdigest()=='88553112839d0a23604171edb03004a15e94f7cc3b174ebb3b9f2e56d3cc2fcc'
off=struct.unpack_from('<Q',fastrpc_raw,40)[0];size,count,idx=struct.unpack_from('<HHH',fastrpc_raw,58)
rows=[struct.unpack_from('<IIQQQQIIQQ',fastrpc_raw,off+i*size) for i in range(count)]
strings=fastrpc_raw[rows[idx][4]:rows[idx][4]+rows[idx][5]]
note=next(r for r in rows if strings[r[0]:].split(b'\\0',1)[0]==b'.note.gnu.build-id')
assert Path('/sys/module/fastrpc/notes/.note.gnu.build-id').read_bytes()==fastrpc_raw[note[4]:note[4]+note[5]]
for name in ['samurai-ssc','iio-sensor-proxy']:
 assert subprocess.run(['rc-service',name,'status'],capture_output=True).returncode==0
sensor_bus=dbus.SystemBus(private=True)
deadline=time.monotonic()+40
while not sensor_bus.name_has_owner('net.hadess.SensorProxy') and time.monotonic()<deadline:time.sleep(.25)
assert sensor_bus.name_has_owner('net.hadess.SensorProxy')
sensor_props=dbus.Interface(sensor_bus.get_object('net.hadess.SensorProxy','/net/hadess/SensorProxy'),'org.freedesktop.DBus.Properties').GetAll('net.hadess.SensorProxy')
assert all(sensor_props[k] for k in ['HasAccelerometer','HasAmbientLight','HasProximity'])
sensor_bus.close()
"""
assert data.count(marker)==1;data=data.replace(marker,extension+marker)
data=data.replace("(out / 'summary.json').write_text","""report.update(boot_fault_free=False,bluetooth_startup_failure_preserved=True,
 fastrpc_candidate_sha256=hashlib.sha256(fastrpc_raw).hexdigest(),fastrpc_candidate_loaded_build_id_verified=True,
 ssc_service_started_automatically=True,sensor_proxy_started_automatically=True,
 sensor_proxy={str(k):sensor_props[k] for k in ['HasAccelerometer','HasAmbientLight','HasProximity','AccelerometerOrientation','LightLevel','LightLevelUnit']})
(out / 'summary.json').write_text""")
try:p=host.ssh('python3 -',input=data.encode(),timeout=125)
except subprocess.CalledProcessError as error:
 (host.PRIVATE/'runtime-collection-failure-private.log').write_bytes(error.stdout+error.stderr)
 print(error.stderr.decode());raise
(host.PRIVATE/'reboot-runtime-host-private.log').write_bytes(p.stdout+p.stderr)
print(p.stdout.decode())
