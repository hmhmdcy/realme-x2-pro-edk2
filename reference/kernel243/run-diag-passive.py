"""One 20-second transport-only probe; no diagnostic or GNSS commands."""
from pathlib import Path
import dbus,hashlib,json,os,subprocess
os.umask(0o077);r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
o=r/'k243-diag-passive-r3';assert not o.exists();o.mkdir(mode=0o700)
tools=r/'k243-diag-tools-r3';b=tools/'diag-passive';build=json.loads((tools/'build-summary.json').read_text());assert hashlib.sha256(b.read_bytes()).hexdigest()==build['binary_sha256']
bus=dbus.SystemBus(private=True);owner=str(bus.get_name_owner('org.freedesktop.ModemManager1'))
objects=dbus.Interface(bus.get_object(owner,'/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();v=next(v for v in objects.values() if 'org.freedesktop.ModemManager1.Modem' in v);loc=v['org.freedesktop.ModemManager1.Modem.Location'];assert int(loc['Enabled'])==0
before_lookup=subprocess.check_output(['qrtr-lookup']);assert not any(line.split() and line.split()[0]=='4097' for line in before_lookup.decode().splitlines())
before=subprocess.check_output(['dmesg']);(o/'dmesg-before-private.txt').write_bytes(before);(o/'lookup-before-private.txt').write_bytes(before_lookup)
env=dict(os.environ);env.pop('LD_PRELOAD',None);env.pop('LD_LIBRARY_PATH',None)
with (o/'events-private.jsonl').open('xb') as out,(o/'stderr-private.txt').open('xb') as err:
 p=subprocess.Popen([str(b)],stdout=out,stderr=err,env=env)
 try:rc=p.wait(timeout=28)
 except subprocess.TimeoutExpired:p.terminate();rc=p.wait(timeout=10)
rows=[json.loads(line) for line in (o/'events-private.jsonl').read_text().splitlines()];last=rows[-1]
assert last['kind']=='cleanup'
after_lookup=subprocess.check_output(['qrtr-lookup']);(o/'lookup-after-private.txt').write_bytes(after_lookup)
after=subprocess.check_output(['dmesg']);(o/'dmesg-after-private.txt').write_bytes(after)
objects=dbus.Interface(bus.get_object(owner,'/org/freedesktop/ModemManager1'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();v=next(v for v in objects.values() if 'org.freedesktop.ModemManager1.Modem' in v)
report=dict(stage=243,program_exit=rc,cleanup=last,no_diag_service_after=not any(line.split() and line.split()[0]=='4097' for line in after_lookup.decode().splitlines()),
 mm_owner_preserved=str(bus.get_name_owner('org.freedesktop.ModemManager1'))==owner,location_enabled=int(v['org.freedesktop.ModemManager1.Modem.Location']['Enabled']),
 fault_delta={k:after.count(s)-before.count(s) for k,s in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()},taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 no_diag_payloads_or_gnss_start=True,no_nv_or_rf_configuration=True)
(o/'summary.json').write_text(json.dumps(report,indent=2)+'\n');bus.close();print(json.dumps(report),flush=True)
assert rc==0 and last['servers_removed']==3 and last['sockets_closed']==4 and report['no_diag_service_after'] and report['mm_owner_preserved']
assert report['location_enabled']==0 and not any(report['fault_delta'].values()) and report['taint']==0
