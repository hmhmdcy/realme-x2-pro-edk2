"""Stage new module/packages, verify old payloads, and preserve matched rollback."""
from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((R/'complete-host-qa-validation.json').read_text())['all_13_package_signatures_and_features_checked']
assert json.loads((R/'built-helper-validation.json').read_text())['negative_r20_missing_gw1_verified']
module=json.loads((R.parent/'kernel272/current-module-build-validation.json').read_text())
binary=P.parent/'kernel272/current-module-build-r1/s5kgw1.ko'
assert hashlib.sha256(binary.read_bytes()).hexdigest()==module['modules']['s5kgw1.ko']['sha256']
runtime=json.loads((R/'runtime-repo-validation.json').read_text());archive=P/'r21-seven-package-repo-private.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==runtime['sha256']
baseline=json.loads((P/'deployment-baseline-private.json').read_text())
stage='/var/lib/samurai/k273-main-candidates'
q=host.ssh('python3 -c '+shlex.quote("from pathlib import Path;import os;os.umask(0o077);Path(%r).mkdir(mode=0o700)"%stage),timeout=15)
for name,path in [('runtime.tar.gz',archive),('s5kgw1.ko',binary)]:
 data=path.read_bytes();digest=hashlib.sha256(data).hexdigest();remote=stage+'/'+name
 code="from pathlib import Path;import hashlib,os,sys;os.umask(0o077);p=Path(%r);assert not p.exists();b=sys.stdin.buffer.read();assert hashlib.sha256(b).hexdigest()==%r;p.write_bytes(b);print(len(b))"%(remote,digest)
 q=host.ssh('python3 -c '+shlex.quote(code),input=data,timeout=30);assert int(q.stdout)==len(data)
args=dict(boot_id=baseline['boot_id'],old_boot_sha256=baseline['boot_partition_sha256'],package_db_sha256=baseline['package_db_sha256'],
 module_sha256=module['modules']['s5kgw1.ko']['sha256'],vermagic=module['vermagic'],old_repo=baseline['old_repo'])
code=r'''
from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,tarfile,traceback
os.umask(0o077);r=Path('/var/lib/samurai');stage=r/'k273-main-candidates';out=r/'k273-main-transaction';out.mkdir(mode=0o700)
state=dict(stage=273,state='staging-preflight',terminal=False,pid=os.getpid(),start_ticks=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]);added=False;dest=None
def save():(out/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
save()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==args['boot_id']
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and os.uname().version.startswith('#183 ')
 assert sha('/lib/apk/db/installed')==args['package_db_sha256']
 assert not Path('/sys/module/s5kgw1').exists()
 assert os.statvfs('/').f_bavail*os.statvfs('/').f_frsize>512*1024*1024
 with tarfile.open(stage/'runtime.tar.gz','r:gz') as tar:
  for m in tar.getmembers():
   assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
   assert m.name=='forward-manifest.json' or m.name.startswith('forward/')
   p=stage/m.name;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);assert not p.exists();p.write_bytes(tar.extractfile(m).read())
 old_dir=Path(args['old_repo']);old=json.loads((old_dir/'forward-manifest.json').read_text());new=json.loads((stage/'forward-manifest.json').read_text())
 assert len(old['packages'])==len(new['packages'])==7 and {x['name'] for x in old['packages']}=={x['name'] for x in new['packages']}
 for pkg in old['packages']:
  expected='0.1.0-r15' if pkg['name'].startswith('samurai-camera-') else '99990.7.2-r20';assert pkg['version']==expected
  for name,item in pkg['files'].items():
   p=Path('/')/name
   if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
   else:assert not p.is_symlink() and sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
 for directory,manifest in [(old_dir,old),(stage,new)]:
  for pkg in manifest['packages']:
   p=directory/'forward'/pkg['file'];assert sha(p)==pkg['sha256'];subprocess.run(['apk','verify',str(p)],capture_output=True,check=True,timeout=20)
  subprocess.run(['apk','verify',str(directory/'forward/packages.adb')],capture_output=True,check=True,timeout=20)
 repos=out/'candidate-repositories.list';repos.write_text('ndx file://'+str(stage/'forward/packages.adb')+'\n')
 q=subprocess.run(['apk','--no-network','--repositories-file',str(repos),'add','--simulate','samurai-camera-stack=0.1.0-r16'],capture_output=True,text=True,timeout=30)
 (out/'forward-simulate-private.log').write_text(q.stdout+q.stderr);assert q.returncode==0
 actions=[x for x in q.stdout.splitlines() if x.startswith('(')];assert len(actions)==7 and all('Upgrading ' in x for x in actions)
 tree=Path('/usr/lib/modules')/os.uname().release;dest=tree/'kernel/drivers/media/i2c/s5kgw1.ko';assert not dest.exists()
 inventory={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')};assert len(inventory)==774
 (out/'module-inventory-before-private.json').write_text(json.dumps(inventory,indent=2)+'\n')
 backup=out/'backup';backup.mkdir(mode=0o700)
 paths=[Path('/lib/apk/db/installed'),Path('/etc/apk/world'),Path('/etc/libcamera/configuration.yaml'),Path('/etc/apk/repositories.d/60-samurai-camera.list'),*[p for p in tree.iterdir() if p.is_file()]]
 for p in paths:
  target=backup/str(p).lstrip('/');target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);shutil.copy2(p,target)
 boot=Path(subprocess.check_output(['findfs','PARTLABEL=boot'],text=True).strip());assert sha(boot)==args['old_boot_sha256']
 shutil.copyfile(boot,out/'boot270-rollback-private.img');assert sha(out/'boot270-rollback-private.img')==args['old_boot_sha256']
 (out/'old-manifest-private.json').write_text(json.dumps(old));(out/'new-manifest-private.json').write_text(json.dumps(new))
 (out/'rollback-repositories.list').write_text('ndx file://'+str(old_dir/'forward/packages.adb')+'\n')
 rollback=out/'rollback-private.tar.gz'
 with tarfile.open(rollback,'w:gz') as tar:
  for p in backup.rglob('*'):
   if p.is_file():tar.add(p,arcname='files/'+str(p.relative_to(backup)),recursive=False)
  for p in [out/'old-manifest-private.json',out/'module-inventory-before-private.json',out/'boot270-rollback-private.img']:
   tar.add(p,arcname=p.name,recursive=False)
  for pkg in old['packages']:tar.add(old_dir/'forward'/pkg['file'],arcname='packages/'+pkg['file'],recursive=False)
  tar.add(old_dir/'forward/packages.adb',arcname='packages/packages.adb',recursive=False)
 assert sha(stage/'s5kgw1.ko')==args['module_sha256']
 assert subprocess.check_output(['modinfo','-F','vermagic',str(stage/'s5kgw1.ko')],text=True).strip()==args['vermagic']
 assert subprocess.check_output(['modinfo','-F','intree',str(stage/'s5kgw1.ko')],text=True).strip()=='Y'
 state['state']='installing-new-unloaded-module';save();shutil.copyfile(stage/'s5kgw1.ko',dest);dest.chmod(0o644);added=True
 subprocess.run(['depmod','-a',os.uname().release],capture_output=True,check=True)
 q=subprocess.run(['modprobe','-n','-v','s5kgw1'],capture_output=True,text=True,check=True);assert 's5kgw1.ko' in q.stdout
 (out/'module-dry-run-private.log').write_text(q.stdout+q.stderr)
 after={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')}
 assert set(after)-set(inventory)=={'kernel/drivers/media/i2c/s5kgw1.ko'} and all(after[n]==v for n,v in inventory.items())
 assert not Path('/sys/module/s5kgw1').exists() and sha('/lib/apk/db/installed')==args['package_db_sha256']
 report=dict(stage=273,new_module_staged=True,new_module_sha256=args['module_sha256'],existing_774_modules_byte_exact=True,
  old_module_count=774,new_module_count=775,no_hot_load_or_unload=True,old49_package_payloads_verified=True,
  old_and_new_signatures_verified=True,native_seven_upgrades_simulated=True,installed_packages_unchanged=True,
  rollback_bytes=rollback.stat().st_size,rollback_sha256=sha(rollback),rollback_boot_sha256=args['old_boot_sha256'])
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');os.sync();state.update(state='terminal',terminal=True,exit_code=0);save();print(json.dumps(report))
except BaseException:
 (out/'failure-private.txt').write_text(traceback.format_exc())
 if added:
  dest.unlink()
  for p in tree.iterdir():
   if p.is_file() and p.name.startswith('modules.'):
    saved=backup/str(p).lstrip('/')
    if saved.exists():shutil.copy2(saved,p)
 state.update(state='failed',terminal=True,exit_code=1);save();raise
'''
q=host.ssh('python3 -',input=('args='+repr(args)+'\n'+code).encode(),timeout=100,check=False)
(P/'stage-response-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0 and q.stdout,'Inspect this transaction before any retry'
d=json.loads(q.stdout);(R/'module-stage-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2),flush=True)
q=host.ssh('cat /var/lib/samurai/k273-main-transaction/rollback-private.tar.gz',timeout=60)
assert len(q.stdout)==d['rollback_bytes'] and hashlib.sha256(q.stdout).hexdigest()==d['rollback_sha256']
(P/'main-rollback-private.tar.gz').write_bytes(q.stdout)
report=dict(stage=273,phone_and_pc_rollback_verified=True,bytes=len(q.stdout),sha256=d['rollback_sha256'],
 contains_old_signed_r20_r15_packages=True,contains_current_boot270_and_depfiles=True,rollback_boot_sha256=d['rollback_boot_sha256'])
(R/'rollback-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
