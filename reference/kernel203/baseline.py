from pathlib import Path
import dbus,hashlib,json,os,shutil,subprocess

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k203-baseline';assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k202r2-runtime/boot-id-private.txt').read_bytes();(out/'boot-id-private.txt').write_bytes(boot)
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
expected={'/usr/sbin/samurai-gnss-assist':'42168f33472d01dbf115ea766487c70d95332aabc8de02c25bdb381cea80af97','/etc/init.d/samurai-gnss-assist':'54b8174507e97badfafba6c373ebf937045c1c85034f094e7de910369af78af3','/usr/bin/ModemManager':'b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'}
assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest for name,digest in expected.items())
(out/'userspace-check.sha256').write_text(''.join(value+'  '+key+'\n' for key,value in expected.items()))
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');loc=props.GetAll('org.freedesktop.ModemManager1.Modem.Location');m=props.GetAll('org.freedesktop.ModemManager1.Modem');assert int(loc['Enabled'])==0 and not bus.name_has_owner('org.freedesktop.GeoClue2');bus.close()
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch['running'] and not watch['active'] and watch['time_prepared'] and watch['worker_starts']==watch['worker_completions']==1 and watch['time_preparation_starts']==watch['time_preparation_completions']==3
pid=int(Path('/run/samurai-gnss-assist.pid').read_text());assert b'/usr/sbin/samurai-gnss-assist' in Path('/proc/%d/cmdline'%pid).read_bytes().split(b'\0')
results={}
for name,command in [('apk-version',['apk','--version']),('apk-help',['apk','--help']),('modemmanager-package',['apk','info','-a','modemmanager']),('helper-ownership',['apk','info','-W','/usr/sbin/samurai-gnss-assist']),('apk-policy',['apk','policy','modemmanager']),('world',['cat','/etc/apk/world'])]:
 p=subprocess.run(command,capture_output=True,text=True,timeout=20);(out/(name+'-private.txt')).write_text(p.stdout+p.stderr);results[name]=dict(returncode=p.returncode,output=p.stdout+p.stderr)
for name in ['installed','scripts.tar','triggers']:
 p=Path('/lib/apk/db')/name
 if p.exists():shutil.copyfile(p,out/('apk-'+name+'-before-private'))
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(value=='running' for value in rp.values())
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log);counts={key:log.count(value) for key,value in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert not any(counts.values())
r=dict(stage=203,fresh_same_boot202r2_verified=True,kernel_build=183,taint=0,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),helper_init_mm191_exact=True,helper_running_idle=True,gnss_enabled=0,mm_power_state=int(m['PowerState']),mm_state=int(m['State']),mm_failed_reason=int(m['StateFailedReason']),remoteprocs=rp,fault_counts=counts,apk_version=results['apk-version']['output'].strip(),helper_package_owned=results['helper-ownership']['returncode']==0,abuild_available=shutil.which('abuild') is not None,apk_database_backed_up=True,no_install_or_transition_performed=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
