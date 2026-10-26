from pathlib import Path
import json
import host
code=b'''from pathlib import Path
import dbus,json,subprocess
out=Path('/var/lib/samurai/k191-dms-mode');out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
p=subprocess.run(['qmicli','-d','qrtr://0','--dms-get-operating-mode'],capture_output=True,timeout=25)
(out/'reply-private.txt').write_bytes(p.stdout+p.stderr);text=p.stdout.decode().lower()
mode=next((name for name in ['online','low-power','offline','resetting','shutting-down','persistent-low-power','mode-only-low-power'] if "'"+name+"'" in text),None)
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties')
power=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'));bus.close()
record=dict(stage=191,read_only=True,qmi_exit=p.returncode,dms_operating_mode=mode,mm_power_state=power)
(out/'summary.json').write_text(json.dumps(record,indent=2)+'\\n');print(json.dumps(record))
'''
p=host.ssh('python3 -',input=code,timeout=35);report=json.loads(p.stdout)
(Path(__file__).resolve().parent/'modem-power-mode-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
