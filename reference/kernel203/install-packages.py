"""One verified APK adoption transaction; inspect its marker before any retry."""
from pathlib import Path
import dbus,hashlib,json,os,re,shutil,stat,subprocess

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k203-package-install';assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k203-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
preflight=root/'k203-package-preflight';proof=json.loads((preflight/'summary.json').read_text());assert proof['no_real_transaction_sent'] and proof['no_other_package_changes']
processes=json.loads((preflight/'processes-private.json').read_text());repo=root/'packages/gnss-203';manifest=json.loads((repo/'package-manifest.json').read_text());assert manifest==json.loads((preflight/'manifest-snapshot-private.json').read_text())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
for item in manifest['packages']:assert sha(repo/(item['name']+'-'+item['version']+'.apk'))==item['sha256']
watch_path=root/'gnss-assist/watch-state.json';watch=json.loads(watch_path.read_text());assert watch['running'] and not watch['active'] and watch['worker_starts']==watch['worker_completions']==1 and watch['time_preparation_starts']==watch['time_preparation_completions']==3
assert int(Path('/run/samurai-gnss-assist.pid').read_text())==processes['helper_pid']
bus=dbus.SystemBus(private=True);daemon=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus');assert str(daemon.GetNameOwner('org.freedesktop.ModemManager1'))==processes['mm_owner']
props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0 and int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==1 and not bus.name_has_owner('org.freedesktop.GeoClue2')
assert sha(Path('/proc/%d/exe'%processes['mm_pid']))==manifest['source_lock']['runtime_binary_sha256']
assert Path('/lib/apk/db/installed').read_bytes()==(root/'k203-baseline/apk-installed-before-private').read_bytes()
backup=out/'before';backup.mkdir(mode=0o700);snapshots={}
paths={Path('/')/relative for item in manifest['packages'] for relative in item['files']}
paths|={Path('/etc/apk/world'),Path('/etc/runlevels/default/samurai-gnss-assist')}
paths|={path for path in Path('/lib/apk/db').iterdir() if path.is_file() and path.name!='lock'}
for path in sorted(paths):
 relative=str(path).removeprefix('/')
 if path.is_symlink():snapshots[relative]=dict(kind='symlink',target=str(path.readlink()))
 elif path.is_file():
  target=backup/relative;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);shutil.copyfile(path,target);snapshots[relative]=dict(kind='file',sha256=sha(target),mode=stat.S_IMODE(path.stat().st_mode))
 else:snapshots[relative]=dict(kind='absent')
(out/'before-manifest-private.json').write_text(json.dumps(snapshots,indent=2)+'\n')
key=root/'k203-packages/samurai-linux-203.rsa.pub';staging=json.loads((root/'k203-packages/staging-manifest-private.json').read_text());assert sha(key)==staging['public_key_sha256'] and sha(repo/'packages.adb')==staging['index_sha256']
global_key=Path('/etc/apk/keys/samurai-linux-203.rsa.pub');configuration=Path('/etc/apk/repositories.d/50-samurai-gnss.list');assert not global_key.exists() and not configuration.exists()
marker=out/'transaction-private.json';assert not marker.exists();state=dict(phase='before-single-adoption',transaction_count=1,source_boot_verified=True,global_key_was_absent=True,repository_configuration_was_absent=True);marker.write_text(json.dumps(state,indent=2)+'\n')
for target,data in [(global_key,key.read_bytes()),(configuration,b'ndx file:///var/lib/samurai/packages/gnss-203/packages.adb\n')]:
 target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_name(target.name+'.new');assert not temporary.exists();temporary.write_bytes(data);temporary.chmod(0o644);os.replace(temporary,target)
command=['apk','--no-network','--keys-dir',str(preflight/'keys'),'--repositories-file',str(preflight/'repositories.list'),'add','samurai-gnss-stack=0.1.0-r0']
state['phase']='single-apk-transaction-submitted';marker.write_text(json.dumps(state,indent=2)+'\n')
p=subprocess.run(command,capture_output=True,text=True,timeout=180);(out/'transaction-output-private.log').write_text(p.stdout+p.stderr);state.update(phase='apk-returned',returncode=p.returncode);marker.write_text(json.dumps(state,indent=2)+'\n');assert p.returncode==0,'Inspect this transaction; do not repeat it'
actions=re.findall(r'\)\s+(Installing|Upgrading|Downgrading|Purging|Reinstalling)\s+([A-Za-z0-9+_.-]+)',p.stdout+p.stderr)
assert [dict(action=action,package=name) for action,name in actions]==proof['solver_actions']
versions={}
for entry in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 fields={line[:1]:line[2:] for line in entry.splitlines() if len(line)>1 and line[1]==':' and line[:1] in ['P','V']}
 if fields.get('P') in {'modemmanager','modemmanager-openrc','modemmanager-udev','libmm-glib','samurai-gnss-assist','samurai-gnss-stack'}:versions[fields['P']]=fields['V']
for item in manifest['packages']:assert versions[item['name']]==item['version']
assert versions['libmm-glib']==manifest['source_lock']['base_package_version']
for item in manifest['packages']:
 for relative,expected in item['files'].items():
  path=Path('/')/relative
  if expected['kind']=='symlink':assert path.is_symlink() and str(path.readlink())==expected['target']
  else:assert sha(path)==expected['sha256'] and stat.S_IMODE(path.stat().st_mode)==expected['mode'],relative
assert str(daemon.GetNameOwner('org.freedesktop.ModemManager1'))==processes['mm_owner']
assert int(daemon.GetConnectionUnixProcessID(processes['mm_owner']))==processes['mm_pid']
assert sha(Path('/proc/%d/exe'%processes['mm_pid']))==manifest['source_lock']['runtime_binary_sha256']
assert int(Path('/run/samurai-gnss-assist.pid').read_text())==processes['helper_pid']
assert json.loads(watch_path.read_text())==watch
assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0 and int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==1;bus.close()
ownership={}
for path,name in [('/usr/sbin/ModemManager','modemmanager'),('/usr/sbin/samurai-gnss-assist','samurai-gnss-assist'),('/etc/init.d/samurai-gnss-assist','samurai-gnss-assist')]:
 result=subprocess.run(['apk','info','-W',path],capture_output=True,text=True,check=True);assert result.stdout.strip().endswith(name+'-'+versions[name]);ownership[path]=name+'-'+versions[name]
assert str(Path('/etc/runlevels/default/samurai-gnss-assist').readlink())==snapshots['etc/runlevels/default/samurai-gnss-assist']['target']
state['phase']='verified-complete';marker.write_text(json.dumps(state,indent=2)+'\n')
r=dict(stage=203,single_package_transaction_complete=True,actions_match_preflight=True,only_five_packages_changed=True,installed_versions=versions,all_payload_bytes_and_modes_exact=True,backend_and_helper_processes_preserved=True,helper_became_apk_owned=True,mm191_became_apk_owned_without_binary_change=True,public_verification_key_and_signed_local_repository_persisted=True,private_signing_key_off_device=True,mm_loaded_executable_inode_retired=os.readlink('/proc/%d/exe'%processes['mm_pid']).endswith(' (deleted)'),gps_enabled=0,mm_power_state=1,no_modem_power_reset_or_partition_flash_sent=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
