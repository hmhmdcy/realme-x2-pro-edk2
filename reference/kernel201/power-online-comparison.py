from pathlib import Path
import dbus,json,subprocess,time
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k201-baseline/boot-id-private.txt').read_bytes()
out=root/'k201-power-online';assert not out.exists();out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True);obj=bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0');props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');api=dbus.Interface(obj,'org.freedesktop.ModemManager1.Modem')
m=props.GetAll('org.freedesktop.ModemManager1.Modem');assert int(m['PowerState'])==1 and int(m['State'])==-1 and int(m['StateFailedReason'])==2 and not m['Bearers']
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0 and not bus.name_has_owner('org.freedesktop.GeoClue2')
def mode(label):
 p=subprocess.run(['qmicli','-d','qrtr://0','--dms-get-operating-mode'],capture_output=True,text=True,timeout=25);(out/(label+'-private.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0;return next((v for v in ['shutting-down','online','low-power','offline'] if "'"+v+"'" in p.stdout),None)
before=mode('before');assert before=='shutting-down'
r=dict(stage=201,fresh_current_power_state_verified=True,power_on_requests=1,modem_reset_requested=False,mode_before=before,reason='Controlled GNSS RF comparison after valid fresh assistance and synchronized UTC',power_state_before=1)
(out/'request.json').write_text(json.dumps(r,indent=2)+'\n')
api.SetPowerState(dbus.UInt32(3),timeout=50);time.sleep(1);r['power_on_ack']=True;r['mode_after']=mode('after');r['power_state_after']=int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'));r['modem_state_after']=int(props.Get('org.freedesktop.ModemManager1.Modem','State'));r['bearers_after']=len(props.Get('org.freedesktop.ModemManager1.Modem','Bearers'));assert r['mode_after']=='online' and r['power_state_after']==3
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');bus.close();print(json.dumps(r))
