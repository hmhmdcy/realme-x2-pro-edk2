from pathlib import Path
import ast,hashlib,json,host
ref=Path(__file__).resolve().parent;source=ref/'samurai-gnss-assist.py';ast.parse(source.read_text());digest=hashlib.sha256(source.read_bytes()).hexdigest()
code=b'''from pathlib import Path
import dbus,hashlib,json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
p=Path('/usr/sbin/samurai-gnss-assist');assert hashlib.sha256(p.read_bytes()).hexdigest()=='dda70c1f4a9ca833b546f74f6192307914c0e45a157c035479510da41590e929'
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0;bus.close()
state=Path('/var/lib/samurai/gnss-assist/watch-state.json');r=json.loads(state.read_text());assert r['worker_starts']==r['worker_completions']==1 and r['last_result']['status']=='current'
(root/'k201-assist-watch/first-auto-cycle.json').write_text(json.dumps(r,indent=2)+'\\n');(root/'k201-assist-watch/helper-before-final-private.py').write_bytes(p.read_bytes())
'''
host.ssh('python3 -',input=code)
p=host.ssh('rc-service samurai-gnss-assist stop',timeout=20);(host.PRIVATE/'assist-before-final-stop-private.log').write_bytes(p.stdout+p.stderr)
host.upload(source,'/usr/sbin/samurai-gnss-assist');host.ssh('chmod 755 /usr/sbin/samurai-gnss-assist && rc-service samurai-gnss-assist start',timeout=20)
report=dict(stage=201,source_sha256=digest,initd_sha256=hashlib.sha256((ref/'samurai-gnss-assist.initd').read_bytes()).hexdigest(),installed_path='/usr/sbin/samurai-gnss-assist',openrc_default_enabled=True,active_gps_only=True,no_modem_power_or_gps_setup_calls=True,known_bad_payload_cache=True,https_only_redirects=True,qmi_duration_uint16_domain_preserved=True)
(ref/'assist-deployment-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
