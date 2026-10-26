from pathlib import Path
import dbus,json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
out=root/'k201-geoclue-test-r2';r=dict(summary_exists=(out/'summary.json').exists())
if (out/'progress.json').exists():r['progress']=json.loads((out/'progress.json').read_text())
bus=dbus.SystemBus(private=True);mp=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');r['gps_enabled']=int(mp.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'));bus.close()
p=subprocess.run(['qmicli','--version'],capture_output=True,text=True);r['qmicli_version']=next((line.strip() for line in p.stdout.splitlines() if 'qmicli' in line.lower()),'unavailable')
p=subprocess.run(['qmicli','--help-loc'],capture_output=True,text=True);r['qmicli_validity_option_available']='--loc-get-predicted-orbits-data-validity' in p.stdout
print(json.dumps(r))
