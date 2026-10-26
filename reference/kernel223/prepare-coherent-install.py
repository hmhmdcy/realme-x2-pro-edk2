"""Generate one guarded module + native signed-package deployment."""
from pathlib import Path
import json

here=Path(__file__).resolve().parent
assert json.loads((here/'control-snapshot-native-validation.json').read_text())['capture_time_control_snapshots_verified']
source=(here/'native-paired-trial.py').read_text()
a=source.index('eventfd=None;event_thread=')
prefix=source[:a].replace("out=root/'k223-paired-sof-trial'", "out=root/'k223-r8-paired-deployment'")
prefix=prefix.replace("state=dict(phase='preflight',commands=[]);save();", "state=dict(phase='preflight',commands=[],package_transaction_sent=False,module_file_replaced=False);save();")
body=r'''
import stat
forward=root/'k223-r8-package-candidates';rollback=root/'k220-r7-package-candidates'
new_manifest=json.loads((forward/'forward-manifest.json').read_text());old_manifest=json.loads((rollback/'forward-manifest.json').read_text())
selected={p['name'] for p in new_manifest['packages']};assert len(selected)==7 and selected=={p['name'] for p in old_manifest['packages']}
assert Path('/lib/apk/db/installed').read_bytes()==(root/'k223-baseline/installed-before-private.txt').read_bytes()
assert Path('/etc/apk/world').read_bytes()==(root/'k223-baseline/world-before-private.txt').read_bytes()
for name,path in [('installed',Path('/lib/apk/db/installed')),('world',Path('/etc/apk/world')),('configuration',Path('/etc/libcamera/configuration.yaml'))]:
 (out/(name+'-before-private')).write_bytes(path.read_bytes())
repo=Path('/etc/apk/repositories.d/60-samurai-camera.list');assert 'k220-r7-package-candidates/forward/packages.adb' in repo.read_text()
old_repo=repo.read_bytes();old_repo_mode=stat.S_IMODE(repo.stat().st_mode);(out/'repository-before-private').write_bytes(old_repo)
old_module_mode=stat.S_IMODE(original.stat().st_mode)
module_root=original
while module_root.parent.name!='modules':module_root=module_root.parent
module_snapshot={str(p.relative_to(module_root)):(hashlib.sha256(p.read_bytes()).hexdigest(),stat.S_IMODE(p.stat().st_mode)) for p in module_root.rglob('*') if p.is_file() and not p.is_symlink() and p.suffix=='.ko'}
assert len(module_snapshot)==772
(out/'modules-before-private.json').write_text(json.dumps(module_snapshot,indent=2)+'\n')

def verify_payload(manifest):
 count=0
 for package in manifest['packages']:
  for relative,item in package['files'].items():
   p=Path('/')/relative
   if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
   else:assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
   count+=1
 return count

assert verify_payload(old_manifest)==49
for directory,manifest in [(forward,new_manifest),(rollback,old_manifest)]:
 for package in manifest['packages']:
  apk=directory/'forward'/package['file'];assert hashlib.sha256(apk.read_bytes()).hexdigest()==package['sha256']
  p=subprocess.run(['apk','verify',str(apk)],capture_output=True,timeout=20);assert p.returncode==0
forward_repos=out/'forward-repositories.list';forward_repos.write_text('ndx file://'+str(forward/'forward/packages.adb')+'\n')
rollback_repos=out/'rollback-repositories.list';rollback_repos.write_text('ndx file://'+str(rollback/'forward/packages.adb')+'\n')
old_requests=[p['name']+'='+p['version'] for p in old_manifest['packages']]
new_requests=['samurai-camera-stack=0.1.0-r3']
def apk_run(label,repositories,requests,simulate=False):
 args=['apk','--no-network','--repositories-file',str(repositories),'add']
 if simulate:args.append('--simulate')
 p=subprocess.run([*args,*requests],capture_output=True,text=True,timeout=60)
 (out/(label+'-private.log')).write_text(p.stdout+p.stderr)
 assert p.returncode==0
 return p.stdout
dry=apk_run('forward-solver',forward_repos,new_requests,True)
actions=[l for l in dry.splitlines() if l.startswith('(')]
assert len(actions)==7 and all('Upgrading ' in l for l in actions)
for package in new_manifest['packages']:assert any(('Upgrading '+package['name']+' (') in l for l in actions)
assert all(p.read_text().strip()=='closed' for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'))
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
success=False;failure=None
try:
 state['phase']='policy-stop-submitted';save();os.kill(int(wp.name),signal.SIGTERM)
 for _ in range(50):
  if not wp.exists():break
  time.sleep(.1)
 assert not wp.exists() and not process_list('wireplumber') and not video_fds()
 assert (camss/'power/runtime_status').read_text().strip()=='suspended'
 state['phase']='original-unbind-submitted';save();(driver/'unbind').write_text('acb3000.camss');assert not (camss/'driver').exists()
 command(['rmmod','qcom_camss']);assert not loaded.exists()
 state.update(phase='packages-submitted',package_transaction_sent=True);save()
 apk_run('native-install',forward_repos,new_requests)
 state['phase']='packages-returned';save();assert verify_payload(new_manifest)==49
 state['phase']='module-replace-submitted';save()
 temp=original.with_name(original.name+'.k223-new');assert not temp.exists();temp.write_bytes(candidate.read_bytes());temp.chmod(old_module_mode)
 with temp.open('rb') as fd:os.fsync(fd.fileno())
 os.replace(temp,original);state['module_file_replaced']=True;save()
 command(['depmod','-a']);command(['modprobe','qcom-camss'])
 assert loaded.read_bytes()==candidate_note and (camss/'driver').exists()
 assert hashlib.sha256(original.read_bytes()).hexdigest()==hashlib.sha256(candidate.read_bytes()).hexdigest()
 restore_graph()
 state['phase']='paired-components-installed';save()
 repo.write_text('ndx file://'+str(forward/'forward/packages.adb')+'\n');repo.chmod(old_repo_mode)
 dry=apk_run('rollback-solver',rollback_repos,old_requests,True)
 actions=[l for l in dry.splitlines() if l.startswith('(')]
 assert len(actions)==7 and all('Downgrading ' in l for l in actions)
 assert Path('/etc/libcamera/configuration.yaml').read_bytes()==(out/'configuration-before-private').read_bytes()
 expected_world=(out/'world-before-private').read_bytes().replace(b'samurai-camera-stack=0.1.0-r2',b'samurai-camera-stack=0.1.0-r3')
 assert Path('/etc/apk/world').read_bytes()==expected_world
 def records(data):
  result={}
  for block in data.decode().split('\n\n'):
   ns=[l[2:] for l in block.splitlines() if l.startswith('P:')]
   if ns:result[ns[0]]=block
  return result
 old=records((out/'installed-before-private').read_bytes());new=records(Path('/lib/apk/db/installed').read_bytes())
 assert len(new)==944 and set(old)==set(new)
 assert all(new[n]==v for n,v in old.items() if n not in selected)
 assert all('V:'+p['version'] in new[p['name']].splitlines() for p in new_manifest['packages'])
 for relative,(digest,mode) in module_snapshot.items():
  p=module_root/relative
  assert stat.S_IMODE(p.stat().st_mode)==mode
  assert hashlib.sha256(p.read_bytes()).hexdigest()==(hashlib.sha256(candidate.read_bytes()).hexdigest() if p==original else digest)
 assert sum(p.is_file() and p.suffix=='.ko' for p in module_root.rglob('*'))==772
 success=True
except BaseException as error:
 failure=repr(error);state.update(phase='failure-restoring-pair',failure=failure);save()
 if loaded.exists():
  if (camss/'driver').exists():(driver/'unbind').write_text('acb3000.camss')
  command(['rmmod','qcom_camss'])
 if state['package_transaction_sent']:
  apk_run('native-rollback',rollback_repos,old_requests)
  Path('/etc/apk/world').write_bytes((out/'world-before-private').read_bytes())
 if state['module_file_replaced']:
  temp=original.with_name(original.name+'.k223-restore');assert not temp.exists();temp.write_bytes((out/'qcom-camss-original.ko').read_bytes());temp.chmod(old_module_mode);os.replace(temp,original)
 command(['depmod','-a']);command(['modprobe','qcom-camss']);assert loaded.read_bytes()==original_note
 repo.write_bytes(old_repo);repo.chmod(old_repo_mode);assert verify_payload(old_manifest)==49
 restore_graph();state['phase']='original-pair-restored';save()
finally:
 if not process_list('wireplumber'):
  user=pwd.getpwuid(10000)
  def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
  with (out/'policy-restart-private.log').open('wb') as log:child=subprocess.Popen(argv,env=env,preexec_fn=demote,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  time.sleep(2);assert child.poll() is None
 assert len(process_list('wireplumber'))==1
 for name,identities in preserved.items():assert {p.name:(p/'stat').read_text().split(') ',1)[1].split()[19] for p in process_list(name)}==identities
if not success:raise RuntimeError('Paired deployment failed; original components restored; inspect private state')
new_wp=process_list('wireplumber')[0];maps=(new_wp/'maps').read_text();(out/'policy-after-maps-private.txt').write_text(maps)
assert 'libcamera.so' in maps and '(deleted)' not in '\n'.join(l for l in maps.splitlines() if '/usr/lib/libcamera' in l)
expected={n:i['sha256'] for package in new_manifest['packages'] for n,i in package['files'].items() if i['kind']=='file'}
for line in maps.splitlines():
 if '/usr/lib/libcamera' in line:
  p=Path(line.split()[-1]);assert hashlib.sha256(p.read_bytes()).hexdigest()==expected[str(p).lstrip('/')]
time.sleep(2);after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after)
faults={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not any(faults.values())
r=dict(stage=223,coherent_driver_and_r8_r3_native_deployment=True,transaction_state='verified',
 camss_module_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),loaded_module_note_verified=True,
 framework_version='99990.7.2-r8',configuration_version='0.1.0-r3',installed_payload_records_verified=49,
 installed_package_count=944,unrelated_937_package_records_unchanged=True,other_771_module_files_and_all_module_modes_preserved=True,
 native_seven_package_upgrade_and_r7_downgrade_solver_passed=True,actual_r7_and_original_camss_rollback_retained=True,
 world_only_stack_version_updated=True,configuration_payload_unchanged=True,graph_and_formats_restored=True,wireplumber_reloaded=True,
 desktop_and_pipewire_identities_preserved=True,new_camera_libraries_mapped=True,
 taint=0,fault_delta=faults,no_flash_or_reboot=True,installed_capture_checks_pending=True)
state.update(phase='verified',result=r);save();(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
# The generator's raw block uses doubled escapes; native code needs one.
body=body.replace('\\\\n','\\n')
compile(prefix+body,'native-coherent-deployment223','exec')
(here/'native-coherent-install.py').write_text(prefix+body)
wrapper='''from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
assert json.loads((here/'control-snapshot-native-validation.json').read_text())['capture_time_control_snapshots_verified']
p=host.ssh('python3 -',input=(here/'native-coherent-install.py').read_bytes(),timeout=180)
(host.PRIVATE/'coherent-install-host-private.log').write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout);(here/'coherent-install-validation.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))
'''
compile(wrapper,'install-coherent223','exec');(here/'install-coherent.py').write_text(wrapper)
print('K223_COHERENT_INSTALL_PREPARED')
