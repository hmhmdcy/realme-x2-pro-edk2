from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import dbus,hashlib,json,os,subprocess,gi
gi.require_version('Qmi','1.0');from gi.repository import Qmi
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k221-baseline/boot-id-private.txt').read_bytes()
out=root/'k221-loc-readonly-r3';assert not (out/'query-private.jsonl').exists()
binary=out/'loc-readonly';assert hashlib.sha256(binary.read_bytes()).hexdigest()=='d7fb4c246f234f144973c4664e900b8c20a68ecd46925ce5f5e5512621b0bc8f'
bus=dbus.SystemBus(private=True);p=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1',(root/'k221-baseline/modem-path-private.txt').read_text()),'org.freedesktop.DBus.Properties');before=p.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(before['Enabled'])==0
env=dict(os.environ);env.pop('LD_LIBRARY_PATH',None);env.pop('LD_PRELOAD',None)
run=subprocess.run([str(binary)],capture_output=True,timeout=145,env=env);(out/'query-private.jsonl').write_bytes(run.stdout);(out/'query-stderr-private.txt').write_bytes(run.stderr)
records=[json.loads(l) for l in run.stdout.splitlines()];queries=[x for x in records if x['kind']=='query'];closed=records[-1]
def uint(row,tag,size):
 raw=bytes.fromhex(row['ind_tlvs'].get(str(tag),''))
 if not raw:return None
 assert len(raw)==size
 return int.from_bytes(raw,'little')
summary=[]
for row in queries:
 item={k:v for k,v in row.items() if k not in ['kind','ind_tlvs']};item['indication_status']=uint(row,1,4)
 if row['ack_error']:item['ack_error_name']=Qmi.ProtocolError(row['ack_error']).value_nick
 if row['message_id']==75:item['operation_mode']=uint(row,16,4)
 elif row['message_id']==191:item['constellations']={name:uint(row,tag,4) for tag,name in enumerate(['gps','glonass','beidou','qzss','galileo','navic'],16)}
 elif row['message_id']==183:item['blacklist_masks']={name:uint(row,tag,8) for tag,name in enumerate(['glonass','beidou','qzss','galileo','sbas','navic','gps'],16)}
 elif row['message_id']==225:item['secondary_band_mask']=uint(row,16,4)
 summary.append(item)
after=p.GetAll('org.freedesktop.ModemManager1.Modem.Location');bus.close();assert all(after[k]==before[k] for k in ['Enabled','SignalsLocation','GpsRefreshRate'])
assert closed['kind']=='cleanup' and closed['client_released'] and closed['device_closed']
assert all(row['matching_ack'] for row in queries)
r=dict(stage=221,program_exit=run.returncode,queries=summary,cleanup=closed,gps_idle_properties_preserved=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()),nv_and_engine_configuration_not_written=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=170);(host.PRIVATE/'loc-query-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'loc-configuration-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
