from pathlib import Path
import dbus,json,os,time
os.umask(0o077)
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k208-baseline/boot-id-private.txt').read_bytes()
out=root/'k208-mm-debug-observer';out.mkdir(mode=0o700)
bus=dbus.SystemBus(private=True)
obj=bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0')
props=dbus.Interface(obj,'org.freedesktop.DBus.Properties');api=dbus.Interface(obj,'org.freedesktop.ModemManager1.Modem.Location')
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))&6==6
seen=set();types={};started=time.monotonic()
with (out/'mm-nmea-private.jsonl').open('x') as stream:
    while time.monotonic()-started<20 and int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))&6==6:
        values=api.GetLocation(timeout=8)
        stream.write(json.dumps(values,default=str)+'\n');stream.flush()
        for key,value in values.items():
            if int(key)!=4:continue
            for text in str(value).replace('\r','').split('\n'):
                if text.startswith('$') and text not in seen:
                    seen.add(text);name=text[1:].split(',',1)[0];types[name]=types.get(name,0)+1
        time.sleep(1)
bus.close()
report=dict(stage=208,existing_mm_session_observed_only=True,no_start_stop=True,nmea_types=types,unique_nmea=len(seen),elapsed_seconds=time.monotonic()-started)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
