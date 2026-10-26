"""One standard MM power-on followed by a bounded GPS comparison; no modem reset."""
from pathlib import Path
import dbus,hashlib,json,math,os,re,subprocess,time
os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k191-online-gps');out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True);service='org.freedesktop.ModemManager1';path='/org/freedesktop/ModemManager1/Modem/0'
obj=bus.get_object(service,path);props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');modem_api=dbus.Interface(obj,service+'.Modem');loc_api=dbus.Interface(obj,service+'.Modem.Location')
control=dbus.Interface(bus.get_object(service,'/org/freedesktop/ModemManager1'),service)
before=props.GetAll(service+'.Modem');loc_before=props.GetAll(service+'.Modem.Location')
assert int(before['State'])==-1 and int(before['PowerState'])==1 and not before['Bearers'] and int(loc_before['Enabled'])==0
assert hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
log_before=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-before-private.txt').write_text(log_before)
def qmi(option,label):
 p=subprocess.run(['qmicli','-d','qrtr://0','--'+option],capture_output=True,timeout=25);(out/(label+'-private.txt')).write_bytes(p.stdout+p.stderr)
 text=p.stdout.decode().lower();return p.returncode,next((m for m in ['online','low-power','offline','resetting','shutting-down','persistent-low-power','mode-only-low-power'] if "'"+m+"'" in text),None),text
exit_code,mode,_=qmi('dms-get-operating-mode','mode-before');assert exit_code==0 and mode=='shutting-down'
report=dict(stage=191,power_on_requests=0,power_on_ack=False,modem_reset_requested=False,mode_before=mode,power_state_before=1,gps_setup_ack=False,gps_cleanup_ack=False,valid_fix=False,valid_gga=0,active_rmc=0,raw_reports=0,cnr_numeric_fields=0,positive_cnr_fields=0,maximum_cnr=None)
seen=set();start=time.monotonic();gps_started=False
try:
 control.SetLogging('DEBUG')
 report['power_on_requests']+=1
 modem_api.SetPowerState(dbus.UInt32(3),timeout=50);report['power_on_ack']=True
 time.sleep(2)
 exit_code,mode,_=qmi('dms-get-operating-mode','mode-after-power-on');report['mode_after_power_on']=mode;report['mode_query_exit']=exit_code
 report['power_state_after_on']=int(props.Get(service+'.Modem','PowerState'))
 for option in ['uim-get-card-status','uim-get-slot-status']:
  _,_,text=qmi(option,option+'-after-on')
  report[option]=[line.strip() for line in text.splitlines() if line.strip().startswith(('card state:','card status:','slot status:'))]
 if exit_code==0 and mode=='online':
  loc_api.SetGpsRefreshRate(dbus.UInt32(1),timeout=10)
  loc_api.Setup(dbus.UInt32(6),dbus.Boolean(False),timeout=35);report['gps_setup_ack']=True;gps_started=True
  deadline=time.monotonic()+90
  with (out/'locations-private.jsonl').open('x') as stream:
   while time.monotonic()<deadline:
    values=loc_api.GetLocation(timeout=8);stream.write(json.dumps(dict(elapsed=time.monotonic()-start,locations=values),default=str)+'\n');stream.flush()
    for key,value in values.items():
     if int(key)==2 and isinstance(value,dict) and 'latitude' in value and 'longitude' in value and all(math.isfinite(float(value[x])) for x in ['latitude','longitude']):report['raw_reports']+=1
     if int(key)!=4:continue
     for sentence in str(value).replace('\r','').split('\n'):
      if not sentence.startswith('$') or sentence in seen:continue
      seen.add(sentence);f=sentence.split('*')[0].split(',');kind=f[0][-3:]
      if kind=='GGA' and len(f)>6 and f[6].isdigit() and int(f[6])>0:report['valid_gga']+=1
      if kind=='RMC' and len(f)>2 and f[2]=='A':report['active_rmc']+=1
      if kind=='GSV':
       for i in range(7,len(f),4):
        try:snr=float(f[i])
        except ValueError:continue
        if math.isfinite(snr):report['cnr_numeric_fields']+=1;report['positive_cnr_fields']+=int(snr>0);report['maximum_cnr']=max(report['maximum_cnr'] or 0,snr)
    time.sleep(1)
except dbus.DBusException as error:
 report['error_name']=error.get_dbus_name();(out/'error-private.txt').write_text(str(error))
finally:
 if gps_started:loc_api.Setup(dbus.UInt32(0),dbus.Boolean(False),timeout=30);report['gps_cleanup_ack']=True
 loc_api.SetGpsRefreshRate(dbus.UInt32(int(loc_before['GpsRefreshRate'])),timeout=10)
 control.SetLogging('INFO');report['logging_restored_to_info']=True
 report['gps_enabled_final']=int(props.Get(service+'.Modem.Location','Enabled'))
 report['power_state_final']=int(props.Get(service+'.Modem','PowerState'))
 report['modem_state_final']=int(props.Get(service+'.Modem','State'))
 report['valid_fix']=bool(report['valid_gga'] or report['active_rmc']);report['elapsed_seconds']=time.monotonic()-start
 log_after=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-after-private.txt').write_text(log_after)
 report['fault_delta']={k:log_after.count(v)-log_before.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',slpi_fatal='fatal error received',modem_fatal='crash detected in modem').items()}
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');bus.close()
print(json.dumps(report))
assert report['gps_enabled_final']==0
