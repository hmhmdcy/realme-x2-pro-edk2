"""Read the failed health assumption without changing Bluetooth state."""
from pathlib import Path
import json
import host
code = r'''
from pathlib import Path
import json,subprocess,dbus
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k236-runtime/boot-id-private.txt').read_bytes()
out=root/'k236-health-failure';assert not out.exists();out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True)
objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
adapters=[dict(powered=bool(v['org.bluez.Adapter1']['Powered']),discovering=bool(v['org.bluez.Adapter1']['Discovering'])) for v in objects.values() if 'org.bluez.Adapter1' in v]
connections=sum(bool(v.get('org.bluez.Device1',{}).get('Connected',False)) for v in objects.values())
bus.close()
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
for service in ['bluetooth','samurai-ssc']:
 result=subprocess.run(['rc-service',service,'status'],capture_output=True,timeout=10)
 (out/(service+'-status-private.log')).write_bytes(result.stdout+result.stderr)
report=dict(stage=236,adapters=adapters,connections=connections,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
            fault_counts={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',bt=b'Frame reassembly failed').items()},no_state_change=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
result = host.ssh('python3 -', input=code.encode(), timeout=30)
(host.PRIVATE / 'health-failure-inspection-private.json').write_bytes(result.stdout)
print(result.stdout.decode().strip())
