"""Stage the signed paired update without changing installed drivers or packages."""
from pathlib import Path
import hashlib, json, shlex
import host
R=Path(__file__).resolve().parent
assert json.loads((R/'complete-host-qa-validation.json').read_text())['all_13_package_signatures_and_features_checked']
assert json.loads((R/'gain-helper-test-validation.json').read_text())['negative_r19_missing_helper_verified']
module=json.loads((R/'current-module-build-validation.json').read_text())
binary=host.PRIVATE/'current-module-build-r3/s5k3m5.ko'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==module['sha256']
repo=json.loads((R/'runtime-repo-validation.json').read_text())
tar=host.PRIVATE/'r20-seven-package-repo-private.tar.gz'
assert hashlib.sha256(tar.read_bytes()).hexdigest()==repo['sha256']
root='/var/lib/samurai/k271-gain-candidates'
host.ssh('python3 -c '+shlex.quote("from pathlib import Path;import os;os.umask(0o077);Path(%r).mkdir(mode=0o700)" % root),timeout=20)
for name,path in [('runtime.tar.gz',tar),('s5k3m5.ko',binary)]:
    data=path.read_bytes();remote=root+'/'+name
    host.ssh('python3 -c '+shlex.quote("from pathlib import Path;Path(%r).write_bytes(b'')" % remote),timeout=20)
    for offset in range(0,len(data),32768):
        code="from pathlib import Path;import sys;p=Path(%r);assert p.stat().st_size==%d;f=p.open('ab');f.write(sys.stdin.buffer.read());f.close()" % (remote,offset)
        host.ssh('python3 -c '+shlex.quote(code),input=data[offset:offset+32768],timeout=20)
    code="from pathlib import Path;import hashlib;p=Path(%r);assert hashlib.sha256(p.read_bytes()).hexdigest()==%r" % (remote,hashlib.sha256(data).hexdigest())
    host.ssh('python3 -c '+shlex.quote(code),timeout=20)
code=r'''
from pathlib import Path
import hashlib,json,os,stat,subprocess,tarfile
os.umask(0o077);r=Path('/var/lib/samurai');stage=r/'k271-gain-candidates';out=r/'k271-gain-transaction';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k270-work/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
with tarfile.open(stage/'runtime.tar.gz','r:gz') as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  assert m.name=='forward-manifest.json' or m.name.startswith('forward/')
  p=stage/m.name;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
old_dir=r/'k268-r19-package-candidates';old=json.loads((old_dir/'forward-manifest.json').read_text());new=json.loads((stage/'forward-manifest.json').read_text())
assert len(old['packages'])==len(new['packages'])==7 and {x['name'] for x in old['packages']}=={x['name'] for x in new['packages']}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify_payload(manifest):
 for pkg in manifest['packages']:
  for name,item in pkg['files'].items():
   p=Path('/')/name
   if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
   else:assert not p.is_symlink() and sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
verify_payload(old)
for directory,manifest in [(old_dir,old),(stage,new)]:
 for pkg in manifest['packages']:
  p=directory/'forward'/pkg['file'];assert sha(p)==pkg['sha256']
  subprocess.run(['apk','verify',str(p)],capture_output=True,check=True,timeout=20)
 subprocess.run(['apk','verify',str(directory/'forward/packages.adb')],capture_output=True,check=True,timeout=20)
repos=out/'candidate-repositories.list';repos.write_text('ndx file://'+str(stage/'forward/packages.adb')+'\n')
q=subprocess.run(['apk','--no-network','--repositories-file',str(repos),'add','--simulate','samurai-camera-stack=0.1.0-r15'],capture_output=True,text=True,timeout=30)
(out/'forward-simulate-private.log').write_text(q.stdout+q.stderr);assert q.returncode==0
actions=[x for x in q.stdout.splitlines() if x.startswith('(')];assert len(actions)==7 and all('Upgrading ' in x for x in actions)
for pkg in new['packages']:assert any('Upgrading '+pkg['name']+' (' in x for x in actions)
tree=Path('/usr/lib/modules')/os.uname().release;module=tree/'kernel/drivers/media/i2c/s5k3m5.ko'
assert sha(module)=='22315c6f3eb233add16e33658bd071dbc973499744b21323adf8b771c1552f72'
assert sha(stage/'s5k3m5.ko')==__MODULE__
inventory={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')};assert len(inventory)==774
(out/'module-inventory-before-private.json').write_text(json.dumps(inventory))
backup=out/'backup';backup.mkdir(mode=0o700)
files=[Path('/lib/apk/db/installed'),Path('/etc/apk/world'),Path('/etc/libcamera/configuration.yaml'),Path('/etc/apk/repositories.d/60-samurai-camera.list'),module,*[p for p in tree.iterdir() if p.is_file()]]
for p in files:
 dest=backup/str(p).lstrip('/');dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());dest.chmod(stat.S_IMODE(p.stat().st_mode))
services=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  comm=(p/'comm').read_text().strip()
  if comm not in ['pipewire','wireplumber','phosh','phoc']:continue
  assert int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000
  row=dict(name=comm,pid=int(p.name),start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19])
  if comm in ['pipewire','wireplumber']:
   assert os.readlink(p/'exe')=='/usr/bin/'+comm
   row['env']={k.decode():v.decode() for entry in (p/'environ').read_bytes().split(b'\0') if b'=' in entry for k,v in [entry.split(b'=',1)]}
   assert not any(x in row['env'] for x in ['LD_LIBRARY_PATH','SPA_PLUGIN_DIR','PIPEWIRE_MODULE_DIR'])
   row['argv']=[x.decode() for x in (p/'cmdline').read_bytes().split(b'\0') if x];row['cwd']=os.readlink(p/'cwd')
   assert row['argv'] in [[comm],['/usr/bin/'+comm]]
  services.append(row)
 except FileNotFoundError:continue
assert len(services)==4 and {x['name'] for x in services}=={'pipewire','wireplumber','phosh','phoc'}
(out/'services-before-private.json').write_text(json.dumps(services))
(out/'old-manifest-private.json').write_text(json.dumps(old));(out/'new-manifest-private.json').write_text(json.dumps(new))
rollback=out/'rollback-repositories.list';rollback.write_text('ndx file://'+str(old_dir/'forward/packages.adb')+'\n')
archive=out/'rollback-private.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for p in backup.rglob('*'):
  if p.is_file():tar.add(p,arcname='files/'+str(p.relative_to(backup)),recursive=False)
 for p in [out/'old-manifest-private.json',out/'module-inventory-before-private.json',out/'services-before-private.json']:
  tar.add(p,arcname=p.name,recursive=False)
 for pkg in old['packages']:tar.add(old_dir/'forward'/pkg['file'],arcname='packages/'+pkg['file'],recursive=False)
 tar.add(old_dir/'forward/packages.adb',arcname='packages/packages.adb',recursive=False)
report=dict(stage=271,new_packages_staged=True,original_seven_payloads_verified=True,old_and_new_signatures_verified=True,native_seven_upgrades_simulated=True,
 module_count=774,module_candidate_sha256=__MODULE__,rollback_bytes=archive.stat().st_size,rollback_sha256=sha(archive),no_packages_or_modules_changed=True)
(out/'preflight-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''.replace('__MODULE__',repr(module['sha256']))
q=host.ssh('python3 -',input=code.encode(),timeout=100,check=False)
(host.PRIVATE/'gain-stage-preflight-response-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect staged files and preflight state before repeating anything'
d=json.loads(q.stdout);(R/'gain-preflight-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
# Export the matched rollback, including original signed packages, before installation.
parts=[]
for offset in range(0,d['rollback_bytes'],32768):
    code="from pathlib import Path;import hashlib,sys;b=Path('/var/lib/samurai/k271-gain-transaction/rollback-private.tar.gz').read_bytes();assert hashlib.sha256(b).hexdigest()==%r;sys.stdout.buffer.write(b[%d:%d])" % (d['rollback_sha256'],offset,offset+32768)
    q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);assert len(q.stdout)==min(32768,d['rollback_bytes']-offset);parts.append(q.stdout)
raw=b''.join(parts);assert hashlib.sha256(raw).hexdigest()==d['rollback_sha256']
(host.PRIVATE/'gain-rollback-private.tar.gz').write_bytes(raw)
(R/'gain-rollback-validation.json').write_text(json.dumps(dict(stage=271,phone_and_pc_copies_verified=True,bytes=len(raw),sha256=d['rollback_sha256'],contains_original_signed_packages_and_module=True),indent=2)+'\n')
print('Paired rollback exported and verified; installed stack remains unchanged.')
