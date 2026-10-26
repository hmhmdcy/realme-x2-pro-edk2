"""Stage a package-only update and export the exact installed r23 rollback."""
from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'complete-host-qa-validation.json').read_text())['all_13_package_signatures_and_features_checked']
proof=json.loads((R/'runtime-repo-validation.json').read_text());data=(P/'r24-seven-package-repo-private.tar.gz').read_bytes()
assert hashlib.sha256(data).hexdigest()==proof['sha256']
remote='/var/lib/samurai/k278-package-candidates/runtime.tar.gz'
host.ssh('python3 -c '+shlex.quote("from pathlib import Path;import os;os.umask(0o077);p=Path(%r);p.parent.mkdir(mode=0o700);p.write_bytes(b'')"%remote),timeout=15)
for offset in range(0,len(data),1024*1024):
 code="from pathlib import Path;import sys;p=Path(%r);assert p.stat().st_size==%d;f=p.open('ab');f.write(sys.stdin.buffer.read());f.close()"%(remote,offset)
 host.ssh('python3 -c '+shlex.quote(code),input=data[offset:offset+1024*1024],timeout=30)
code=r'''
from pathlib import Path
import hashlib,json,os,stat,subprocess,tarfile
os.umask(0o077);r=Path('/var/lib/samurai');stage=r/'k278-package-candidates';out=r/'k278-package-transaction';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k276-work/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert not Path('/usr/share/libcamera/ipa/simple/s5kgw1.yaml').exists(),'Existing module profile requires inspection before replacement'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(stage/'runtime.tar.gz')==REPO_SHA
with tarfile.open(stage/'runtime.tar.gz','r:gz') as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  assert m.name=='forward-manifest.json' or m.name.startswith('forward/')
  p=stage/m.name;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
old_dir=r/'k277-package-candidates';old=json.loads((old_dir/'forward-manifest.json').read_text());new=json.loads((stage/'forward-manifest.json').read_text())
assert len(old['packages'])==len(new['packages'])==7 and {p['name'] for p in old['packages']}=={p['name'] for p in new['packages']}
for pkg in old['packages']:
 assert pkg['version']==('0.1.0-r18' if pkg['name'].startswith('samurai-camera-') else '99990.7.2-r23')
 for name,item in pkg['files'].items():
  p=Path('/')/name
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert not p.is_symlink() and sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
for directory,manifest in [(old_dir,old),(stage,new)]:
 for pkg in manifest['packages']:
  p=directory/'forward'/pkg['file'];assert sha(p)==pkg['sha256'];subprocess.run(['apk','verify',str(p)],capture_output=True,check=True,timeout=15)
 subprocess.run(['apk','verify',str(directory/'forward/packages.adb')],capture_output=True,check=True,timeout=15)
(out/'candidate-repositories.list').write_text('ndx file://'+str(stage/'forward/packages.adb')+'\n')
(out/'rollback-repositories.list').write_text('ndx file://'+str(old_dir/'forward/packages.adb')+'\n')
q=subprocess.run(['apk','--no-network','--repositories-file',str(out/'candidate-repositories.list'),'add','--simulate','samurai-camera-stack=0.1.0-r19'],capture_output=True,text=True,timeout=30)
(out/'forward-simulate-private.log').write_text(q.stdout+q.stderr);assert q.returncode==0
actions=[x for x in q.stdout.splitlines() if x.startswith('(')];assert len(actions)==7 and all('Upgrading ' in x for x in actions)
tree=Path('/usr/lib/modules')/os.uname().release;inventory={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')};assert len(inventory)==776
(out/'module-inventory-before-private.json').write_text(json.dumps(inventory))
backup=out/'backup';backup.mkdir(mode=0o700)
for p in [Path('/lib/apk/db/installed'),Path('/etc/apk/world'),Path('/etc/libcamera/configuration.yaml'),Path('/etc/apk/repositories.d/60-samurai-camera.list')]:
 dest=backup/str(p).lstrip('/');dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());dest.chmod(stat.S_IMODE(p.stat().st_mode))
services=[];holders=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  comm=(p/'comm').read_text().strip()
  if (p/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z':continue
  maps=(p/'maps').read_text()
  if '/usr/lib/libcamera' in maps:holders.append(comm)
  if comm not in ['pipewire','wireplumber','phosh','phoc']:continue
  assert int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000
  row=dict(name=comm,pid=int(p.name),start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19])
  if comm in ['pipewire','wireplumber']:
   assert os.readlink(p/'exe')=='/usr/bin/'+comm
   row['env']={k.decode():v.decode() for e in (p/'environ').read_bytes().split(b'\0') if b'=' in e for k,v in [e.split(b'=',1)]}
   assert not any(k in row['env'] for k in ['LD_LIBRARY_PATH','SPA_PLUGIN_DIR','PIPEWIRE_MODULE_DIR'])
   row['argv']=[x.decode() for x in (p/'cmdline').read_bytes().split(b'\0') if x];row['cwd']=os.readlink(p/'cwd');assert row['argv'] in [[comm],['/usr/bin/'+comm]]
  services.append(row)
 except FileNotFoundError:continue
assert len(services)==4 and {x['name'] for x in services}=={'pipewire','wireplumber','phosh','phoc'}
assert set(holders).issubset({'pipewire','wireplumber'}),holders
(out/'services-before-private.json').write_text(json.dumps(services))
(out/'old-manifest-private.json').write_text(json.dumps(old));(out/'new-manifest-private.json').write_text(json.dumps(new))
archive=out/'rollback-private.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for p in backup.rglob('*'):
  if p.is_file():tar.add(p,arcname='files/'+str(p.relative_to(backup)),recursive=False)
 for name in ['old-manifest-private.json','module-inventory-before-private.json','services-before-private.json']:tar.add(out/name,arcname=name,recursive=False)
 for pkg in old['packages']:tar.add(old_dir/'forward'/pkg['file'],arcname='packages/'+pkg['file'],recursive=False)
 tar.add(old_dir/'forward/packages.adb',arcname='packages/packages.adb',recursive=False)
report=dict(stage=278,new_packages_staged=True,original_seven_payloads_verified=True,old_and_new_signatures_verified=True,native_seven_upgrades_simulated=True,
 module_count=776,rollback_bytes=archive.stat().st_size,rollback_sha256=sha(archive),no_packages_or_modules_changed=True)
(out/'preflight-summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''.replace('REPO_SHA',repr(proof['sha256']))
response=P/'stage-response-private.log';assert not response.exists();response.write_bytes(b'SUBMISSION INTENT: inspect existing k278-package-transaction before retry.\n')
q=host.ssh('python3 -',input=code.encode(),timeout=150,check=False);response.write_bytes(q.stdout+q.stderr);assert q.returncode==0 and q.stdout
d=json.loads(q.stdout);(R/'package-preflight-validation.json').write_text(json.dumps(d,indent=2)+'\n')
fetch="from pathlib import Path;import hashlib,sys;p=Path('/var/lib/samurai/k278-package-transaction/rollback-private.tar.gz');b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==%r;sys.stdout.buffer.write(b)"%d['rollback_sha256']
q=host.ssh('python3 -c '+shlex.quote(fetch),timeout=40);assert len(q.stdout)==d['rollback_bytes'] and hashlib.sha256(q.stdout).hexdigest()==d['rollback_sha256']
(P/'package-rollback-private.tar.gz').write_bytes(q.stdout)
(R/'rollback-validation.json').write_text(json.dumps(dict(stage=278,phone_and_pc_copies_verified=True,bytes=len(q.stdout),sha256=d['rollback_sha256'],original_signed_r23_r18_packages=True,no_kernel_or_boot_changes=True),indent=2)+'\n')
print(json.dumps(d,indent=2));print('Exact r23 rollback exported and verified')
