from pathlib import Path
import dbus,hashlib,json,os,re,shutil,stat,subprocess

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k203-package-preflight';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k203-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
repo=root/'packages/gnss-203';manifest=json.loads((repo/'package-manifest.json').read_text());staging=json.loads((root/'k203-packages/staging-manifest-private.json').read_text())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(repo/'packages.adb')==staging['index_sha256']
key=root/'k203-packages/samurai-linux-203.rsa.pub';assert sha(key)==staging['public_key_sha256']
keys=out/'keys';keys.mkdir(mode=0o700)
for original in Path('/etc/apk/keys').glob('*.pub'):shutil.copyfile(original,keys/original.name)
shutil.copyfile(key,keys/key.name)
for path in [repo/'packages.adb',*[repo/(item['name']+'-'+item['version']+'.apk') for item in manifest['packages']]]:
 p=subprocess.run(['apk','--keys-dir',str(keys),'verify',str(path)],capture_output=True,timeout=30);assert p.returncode==0; (out/(path.name+'-verify-private.log')).write_bytes(p.stdout+p.stderr)
new_files=[]
for item in manifest['packages']:
 package=repo/(item['name']+'-'+item['version']+'.apk');assert sha(package)==item['sha256']
 for relative,expected in item['files'].items():
  assert '..' not in Path(relative).parts and relative.startswith(('usr/','etc/'))
  path=Path('/')/relative
  if not path.exists() and not path.is_symlink():new_files.append(relative);continue
  if expected['kind']=='symlink':assert path.is_symlink() and str(path.readlink())==expected['target'],relative
  else:assert path.is_file() and sha(path)==expected['sha256'] and stat.S_IMODE(path.stat().st_mode)==expected['mode'],relative
assert new_files==['usr/share/doc/samurai-gnss-assist/NOTICE']
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch['running'] and not watch['active'] and watch['worker_starts']==watch['worker_completions']==1 and watch['time_preparation_starts']==watch['time_preparation_completions']==3
bus=dbus.SystemBus(private=True);props=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');assert int(props.Get('org.freedesktop.ModemManager1.Modem.Location','Enabled'))==0 and int(props.Get('org.freedesktop.ModemManager1.Modem','PowerState'))==1
assert not bus.name_has_owner('org.freedesktop.GeoClue2')
daemon=dbus.Interface(bus.get_object('org.freedesktop.DBus','/org/freedesktop/DBus'),'org.freedesktop.DBus');owner=str(daemon.GetNameOwner('org.freedesktop.ModemManager1'));pid=int(daemon.GetConnectionUnixProcessID(owner));helper_pid=int(Path('/run/samurai-gnss-assist.pid').read_text())
assert sha(Path('/proc/%d/exe'%pid))==manifest['source_lock']['runtime_binary_sha256'];bus.close()
db=Path('/lib/apk/db/installed').read_bytes();assert db==(root/'k203-baseline/apk-installed-before-private').read_bytes()
repositories=out/'repositories.list';repositories.write_text('ndx file:///var/lib/samurai/packages/gnss-203/packages.adb\n')
command=['apk','--no-network','--keys-dir',str(keys),'--repositories-file',str(repositories),'add','--simulate','samurai-gnss-stack=0.1.0-r0']
p=subprocess.run(command,capture_output=True,text=True,timeout=60);(out/'simulate-private.log').write_text(p.stdout+p.stderr)
assert p.returncode==0,'Inspect solver output; no real transaction requested'
actions=re.findall(r'\)\s+(Installing|Upgrading|Downgrading|Purging|Reinstalling)\s+([A-Za-z0-9+_.-]+)',p.stdout+p.stderr)
expected={'modemmanager','modemmanager-openrc','modemmanager-udev','samurai-gnss-assist','samurai-gnss-stack'}
assert {name for action,name in actions}==expected and len(actions)==5,actions
assert all(action==('Installing' if name.startswith('samurai-') else 'Upgrading') for action,name in actions)
assert db==Path('/lib/apk/db/installed').read_bytes() and helper_pid==int(Path('/run/samurai-gnss-assist.pid').read_text())
(out/'processes-private.json').write_text(json.dumps(dict(mm_owner=owner,mm_pid=pid,helper_pid=helper_pid),indent=2)+'\n')
(out/'manifest-snapshot-private.json').write_text(json.dumps(manifest,indent=2)+'\n')
r=dict(stage=203,current_boot_and_idle_verified=True,all_five_package_and_repository_signatures_verified=True,all_existing_payload_bytes_and_modes_already_match=True,new_document_only=new_files,solver_actions=[dict(action=action,package=name) for action,name in actions],no_other_package_changes=True,package_database_and_helper_process_unchanged=True,no_real_transaction_sent=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
