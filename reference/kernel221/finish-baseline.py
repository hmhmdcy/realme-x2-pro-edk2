from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import dbus,json,os,re,subprocess,gi
root=Path('/var/lib/samurai');out=root/'k221-baseline'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(out/'boot-id-private.txt').read_bytes()
packages={}
for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 fields={l[0]:l[2:] for l in block.splitlines() if len(l)>1 and l[1]==':' and l[0] in 'PV'}
 if 'P' in fields:packages[fields['P']]=fields.get('V')
assert packages['libcamera']=='99990.7.2-r7' and packages['libcamera-ipa']=='99990.7.2-r7' and packages['samurai-camera-config']=='0.1.0-r2'
bus=dbus.SystemBus(private=True);p=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1',(out/'modem-path-private.txt').read_text()),'org.freedesktop.DBus.Properties')
modem=p.GetAll('org.freedesktop.ModemManager1.Modem');loc=p.GetAll('org.freedesktop.ModemManager1.Modem.Location');bus.close()
gps=dict(enabled=int(loc['Enabled']),signals=bool(loc['SignalsLocation']),rate=int(loc['GpsRefreshRate']));assert gps==dict(enabled=0,signals=False,rate=30)
queries={}
for option in ['dms-get-operating-mode','loc-get-operation-mode','loc-get-engine-lock','loc-get-nmea-types']:
 text=(out/(option+'-private.txt')).read_text()
 lines=[l.strip() for l in text.splitlines() if re.search(r'(?:[Mm]ode|[Ll]ock|NMEA).*:',l) and not l.startswith('[')]
 queries[option]=lines
gi.require_version('Qmi','1.0');from gi.repository import Qmi,GObject
methods=[x for x in dir(Qmi.ClientLoc) if any(s in x for s in ['lock','operation_mode','gnss','constellation','system_info'])]
signals=list(GObject.signal_list_names(Qmi.ClientLoc))
(out/'gi-private.json').write_text(json.dumps(dict(methods=methods,signals=signals),indent=2)+'\n')
modem_summary={k:int(modem[k]) for k in ['State','StateFailedReason','PowerState','UnlockRequired']};modem_summary.update(sim_path_present=str(modem.get('Sim','/'))!='/',bearer_count=len(modem.get('Bearers',[])))
r=dict(stage=221,current219_boot_authenticated=True,current_camera_stack_preserved=True,modem=modem_summary,gps=gps,queries=queries,loc_methods=methods,taint=int(Path('/proc/sys/kernel/tainted').read_text()),no_engine_start_or_reboot=True,initial_assertion_was_package_cli_format=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=40);(host.PRIVATE/'baseline-finish-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'baseline-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
state=json.loads((host.PRIVATE/'current-work-private.json').read_text());state.update(guard='/var/lib/samurai/k221-baseline/boot-id-private.txt',state='Read-only GNSS/modem baseline complete; initial package CLI assertion recorded, r7/r2 verified from installed DB')
(host.PRIVATE/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n')
