from pathlib import Path
import hashlib,json,tarfile
import host
code=b'''from pathlib import Path
import dbus,hashlib,io,json,os,subprocess,tarfile
os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k189r2-reboot-runtime/boot-id-private.txt').read_bytes()
root=Path('/var/lib/samurai');out=root/'k191-radio-final';out.mkdir(mode=0o700)
results={}
for option in ['dms-get-operating-mode','uim-get-card-status','uim-get-slot-status']:
 p=subprocess.run(['qmicli','-d','qrtr://0','--'+option],capture_output=True,timeout=25);(out/(option+'-private.txt')).write_bytes(p.stdout+p.stderr)
 text=p.stdout.decode();results[option]=dict(exit=p.returncode,state_lines=[line.strip() for line in text.splitlines() if line.lower().strip().startswith(('mode:','card state:','card status:','slot status:'))])
 if option=='dms-get-operating-mode':results[option]['online']="'online'" in text.lower()
bus=dbus.SystemBus(private=True);service='org.freedesktop.ModemManager1';manager='/org/freedesktop/ModemManager1'
daemon=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus');pid=int(daemon.GetConnectionUnixProcessID(daemon.GetNameOwner(service)))
assert hashlib.sha256((Path('/proc')/str(pid)/'exe').read_bytes()).hexdigest()=='b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
objects=dbus.Interface(bus.get_object(service,manager),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();values=next(v for v in objects.values() if service+'.Modem.Location' in v)
loc=values[service+'.Modem.Location'];modem=values[service+'.Modem'];assert int(loc['Enabled'])==0 and not modem['Bearers'] and int(modem['PowerState'])==3
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in rp.values())
log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-private.txt').write_text(log);baseline=json.loads((root/'k191-baseline/summary.json').read_text())
counts={k:log.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',slpi_fatal='fatal error received',bluetooth='Frame reassembly failed').items()};deltas={k:counts[k]-baseline['fault_counts'][k] for k in counts};assert all(v==0 for v in deltas.values())
nv=subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],capture_output=True);(out/'nv-source-check-private.log').write_bytes(nv.stdout+nv.stderr);assert nv.returncode==0
report=dict(stage=191,same_boot_as189=True,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),taint=int(Path('/proc/sys/kernel/tainted').read_text()),mm191_binary_running=True,
 modem_power_state=int(modem['PowerState']),modem_state=int(modem['State']),failed_reason=int(modem['StateFailedReason']),gps_enabled=int(loc['Enabled']),gps_refresh_rate=int(loc['GpsRefreshRate']),bearers=len(modem['Bearers']),remoteprocs=rp,
 qmi_results=results,fault_counts=counts,fault_deltas=deltas,nv_source_manifest_unchanged=True,modem_reset_requested=False,gps_fix_proven=False)
assert results['dms-get-operating-mode']['online']
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\\n');bus.close()
files=[]
for dirname in ['k191-dms-mode','k191-active-power','k191-uim-status','k191-online-gps','k191-radio-final']:
 files.extend(p for p in (root/dirname).rglob('*') if p.is_file() and not p.is_symlink())
files.append(root/'k191-mm-deploy/daemon-debug-private.log')
blobs={str(p.relative_to(root)):p.read_bytes() for p in files}
manifest={name:hashlib.sha256(raw).hexdigest() for name,raw in blobs.items()}
blobs['manifest-private.json']=json.dumps(manifest,indent=2).encode()
archive=out/'radio-supplement-private.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for name,raw in blobs.items():
  info=tarfile.TarInfo(name);info.size=len(raw);info.mode=0o600;tar.addfile(info,io.BytesIO(raw))
record=dict(files=len(manifest),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),final=report)
(out/'export-summary.json').write_text(json.dumps(record,indent=2)+'\\n');print(json.dumps(record))
'''
p=host.ssh('python3 -',input=code,timeout=120);record=json.loads(p.stdout);archive=host.PRIVATE/'radio-supplement-private.tar.gz'
host.download('/var/lib/samurai/k191-radio-final/radio-supplement-private.tar.gz',archive);assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['archive_sha256']
ref=Path(__file__).resolve().parent
with tarfile.open(archive) as tar:
 for name,digest in json.load(tar.extractfile('manifest-private.json')).items():assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==digest
 for target,source in [('active-gps-power-validation.json','k191-active-power/summary.json'),('online-gps-validation.json','k191-online-gps/summary.json')]:
  (ref/target).write_text(json.dumps(json.load(tar.extractfile(source)),indent=2)+'\n')
 before={}
 for name in ['uim-get-card-status','uim-get-slot-status']:
  text=tar.extractfile('k191-uim-status/'+name+'-private.txt').read().decode()
  before[name]=[line.strip() for line in text.splitlines() if line.lower().strip().startswith(('card state:','card status:','slot status:'))]
 comparison=dict(before_power_on=before,after_power_on_fresh=record['final']['qmi_results'],original_state_only_parser_missed_unquoted_and_detailed_states=True)
 (ref/'uim-power-comparison-validation.json').write_text(json.dumps(comparison,indent=2)+'\n')
(ref/'radio-final-validation.json').write_text(json.dumps(record.pop('final'),indent=2)+'\n')
record.update(host_archive_hash_verified=True,all_member_hashes_verified=True,byte_snapshot_used_for_live_logs=True)
(ref/'radio-supplement-export-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
