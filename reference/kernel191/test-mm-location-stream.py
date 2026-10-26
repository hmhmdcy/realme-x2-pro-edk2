"""Use ModemManager's packaged GPS backend; retain coordinates only in private logs."""
from pathlib import Path
import collections,dbus,hashlib,json,math,os,subprocess,time

os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k191-mm-stream');assert not out.exists();out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True)
obj=bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0')
props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');api=dbus.Interface(obj,'org.freedesktop.ModemManager1.Modem.Location')
before=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');assert int(before['Enabled'])==0
assert not before['SignalsLocation']
validity=json.loads(Path('/var/lib/samurai/k191-validity-after/summary.json').read_text());assert validity['duration_hours']>0
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
manager=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1'),'org.freedesktop.ModemManager1')
initial_log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-before-private.txt').write_text(initial_log)
summary=dict(stage=191,requested_sources=6,setup_ack=False,cleanup_ack=False,polls=0,nmea_distinct_sentences=0,
 nmea_checksum_failures=0,nmea_types={},valid_gga_sentences=0,active_rmc_sentences=0,gps_raw_reports=0,
 valid_gps_fix=False,global_location_signaling_enabled=False)
seen=set();counts=collections.Counter();start=time.monotonic()
try:
 manager.SetLogging('DEBUG')
 api.SetGpsRefreshRate(dbus.UInt32(1),timeout=10)
 api.Setup(dbus.UInt32(6),dbus.Boolean(False),timeout=45);summary['setup_ack']=True
 deadline=time.monotonic()+300
 with (out/'locations-private.jsonl').open('x') as stream:
  while time.monotonic()<deadline:
   values=api.GetLocation(timeout=8);summary['polls']+=1
   stream.write(json.dumps(dict(elapsed=time.monotonic()-start,locations=values),default=str)+'\n');stream.flush()
   for kind,value in values.items():
    if int(kind)==2 and isinstance(value,dict) and 'latitude' in value and 'longitude' in value:
     if math.isfinite(float(value['latitude'])) and math.isfinite(float(value['longitude'])):summary['gps_raw_reports']+=1
    if int(kind)!=4:continue
    for line in str(value).replace('\r','').split('\n'):
     if not line.startswith('$') or line in seen:continue
     seen.add(line)
     if '*' not in line:summary['nmea_checksum_failures']+=1;continue
     body,checksum=line[1:].rsplit('*',1);actual=0
     for char in body:actual^=ord(char)
     try:valid=int(checksum[:2],16)==actual
     except ValueError:valid=False
     if not valid:summary['nmea_checksum_failures']+=1;continue
     fields=body.split(',');kind=fields[0][-3:];counts[kind]+=1
     if kind=='GGA' and len(fields)>6 and fields[6].isdigit() and int(fields[6])>0:summary['valid_gga_sentences']+=1
     if kind=='RMC' and len(fields)>2 and fields[2]=='A':summary['active_rmc_sentences']+=1
   time.sleep(1)
finally:
 if summary['setup_ack']:
  api.Setup(dbus.UInt32(0),dbus.Boolean(False),timeout=30);summary['cleanup_ack']=True
 api.SetGpsRefreshRate(dbus.UInt32(int(before['GpsRefreshRate'])),timeout=10)
 manager.SetLogging('INFO');summary['logging_restored_to_info']=True
 final=props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
 summary.update(final_enabled=int(final['Enabled']),refresh_rate_restored=int(final['GpsRefreshRate'])==int(before['GpsRefreshRate']),
  nmea_distinct_sentences=len(seen),nmea_types=dict(counts),elapsed_seconds=time.monotonic()-start,
  valid_gps_fix=bool(summary['valid_gga_sentences'] or summary['active_rmc_sentences']))
 final_log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-after-private.txt').write_text(final_log)
 assert final_log.startswith(initial_log);extra=final_log[len(initial_log):]
 summary['fault_delta']={k:extra.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',slpi_fatal='fatal error received',modem_crash='crash detected in modem').items()}
 bus.close();(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
assert summary['setup_ack'] and summary['cleanup_ack'] and summary['final_enabled']==0 and summary['refresh_rate_restored']
