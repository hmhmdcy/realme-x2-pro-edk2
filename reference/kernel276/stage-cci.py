"""Replace only the unloaded-on-next-boot CCI file, preserving the actual boot275/module pair."""
from pathlib import Path
import hashlib,json,shlex
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;proof=json.loads((R/'current-module-build-validation.json').read_text());binary=Path(proof['build_directory'])/'i2c-qcom-cci.ko';assert hashlib.sha256(binary.read_bytes()).hexdigest()==proof['module_sha256']
expected=json.loads((R.parent/'kernel275/build-package-validation.json').read_text())['boot_sha256'];response=P/'stage-response-private.log';assert not response.exists()
remote='/var/lib/samurai/k276-cci-candidate.ko';code="from pathlib import Path;import sys,hashlib,os;os.umask(0o077);p=Path(%r);assert not p.exists();b=sys.stdin.buffer.read();assert hashlib.sha256(b).hexdigest()==%r;p.write_bytes(b)"%(remote,proof['module_sha256'])
host.ssh('python3 -c '+shlex.quote(code),input=binary.read_bytes(),timeout=15)
code=r'''
from pathlib import Path
import hashlib,json,os,shutil,struct,subprocess,tarfile,traceback
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k276-cci-transaction';out.mkdir(mode=0o700)
state=dict(state='preflight',terminal=False,pid=os.getpid());marker=out/'state-private.json'
def save():marker.write_text(json.dumps(state,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def note(p):
 b=Path(p).read_bytes();off=struct.unpack_from('<Q',b,40)[0];size,count,index=struct.unpack_from('<HHH',b,58);sec=[struct.unpack_from('<IIQQQQIIQQ',b,off+i*size) for i in range(count)];names=b[sec[index][4]:sec[index][4]+sec[index][5]]
 return next(b[s[4]:s[4]+s[5]] for s in sec if names[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
save();changed=False
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k275-work/boot-id-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 assert all(Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip()=='suspended' for n in ['6-0010','7-0010','8-002d','9-0010','6-0072'])
 tree=Path('/usr/lib/modules')/os.uname().release;dest=Path(subprocess.check_output(['modinfo','-n','i2c_qcom_cci'],text=True).strip());assert dest==tree/'kernel/drivers/i2c/busses/i2c-qcom-cci.ko'
 assert Path('/sys/module/i2c_qcom_cci/notes/.note.gnu.build-id').read_bytes()==note(dest)
 inventory={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')};assert len(inventory)==776
 boot=Path(subprocess.check_output(['findfs','PARTLABEL=boot'],text=True).strip());assert sha(boot)==args['old_boot_sha256']
 before_db=sha('/lib/apk/db/installed');backup=out/'backup';backup.mkdir(mode=0o700)
 paths=[dest,*[p for p in tree.iterdir() if p.is_file()],Path('/lib/apk/db/installed'),Path('/etc/apk/world'),Path('/etc/libcamera/configuration.yaml'),Path('/etc/apk/repositories.d/60-samurai-camera.list')]
 for p in paths:q=backup/str(p).lstrip('/');q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 shutil.copyfile(boot,out/'boot275-rollback-private.img');assert sha(out/'boot275-rollback-private.img')==args['old_boot_sha256']
 (out/'module-inventory-before-private.json').write_text(json.dumps(inventory,indent=2)+'\n')
 rollback=out/'rollback-private.tar.gz'
 with tarfile.open(rollback,'w:gz') as tar:
  for p in backup.rglob('*'):
   if p.is_file():tar.add(p,arcname='files/'+str(p.relative_to(backup)),recursive=False)
  for p in [out/'boot275-rollback-private.img',out/'module-inventory-before-private.json']:tar.add(p,arcname=p.name,recursive=False)
 candidate=root/'k276-cci-candidate.ko';assert sha(candidate)==args['module_sha256'];assert subprocess.check_output(['modinfo','-F','vermagic',str(candidate)],text=True).strip()==args['vermagic']
 state.update(state='replacing-disk-module-only');save();shutil.copyfile(candidate,dest);dest.chmod(0o644);changed=True;subprocess.run(['depmod','-a',os.uname().release],capture_output=True,check=True)
 after={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')};assert set(after)==set(inventory) and [n for n in after if after[n]!=inventory[n]]==['kernel/drivers/i2c/busses/i2c-qcom-cci.ko']
 assert sha('/lib/apk/db/installed')==before_db
 result=dict(stage=276,new_module_staged=True,new_cci_sha256=args['module_sha256'],old_cci_sha256=inventory['kernel/drivers/i2c/busses/i2c-qcom-cci.ko'],module_count=776,other775_modules_unchanged=True,packages_unchanged=True,loaded_cci_still_old=True,no_hot_unload=True,rollback_bytes=rollback.stat().st_size,rollback_sha256=sha(rollback),rollback_boot_sha256=args['old_boot_sha256'])
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');os.sync();state.update(state='terminal',terminal=True,exit_code=0);save();print(json.dumps(result))
except BaseException:
 (out/'failure-private.txt').write_text(traceback.format_exc())
 if changed:
  for p in backup.rglob('*'):
   name=str(p.relative_to(backup))
   if p.is_file() and name.startswith(str(tree).lstrip('/')):shutil.copy2(p,Path('/')/name)
 state.update(state='failed',terminal=True,exit_code=1);save();raise
'''
args=dict(old_boot_sha256=expected,module_sha256=proof['module_sha256'],vermagic=proof['vermagic']);response.write_bytes(b'SUBMISSION INTENT: inspect k276-cci-transaction if response is lost.\n')
q=host.ssh('python3 -',input=('args='+repr(args)+'\n'+code).encode(),timeout=100,check=False);response.write_bytes(q.stdout+q.stderr);assert q.returncode==0 and q.stdout
d=json.loads(q.stdout);(R/'module-stage-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2),flush=True)
q=host.ssh('cat /var/lib/samurai/k276-cci-transaction/rollback-private.tar.gz',timeout=60);assert len(q.stdout)==d['rollback_bytes'] and hashlib.sha256(q.stdout).hexdigest()==d['rollback_sha256'];(P/'cci-rollback-private.tar.gz').write_bytes(q.stdout)
(R/'rollback-validation.json').write_text(json.dumps(dict(stage=276,phone_and_pc_rollback_verified=True,bytes=len(q.stdout),sha256=d['rollback_sha256'],contains_actual_boot275_and_old_cci=True,packages_were_not_changed=True),indent=2)+'\n')
print('Matched CCI and boot275 rollback verified on phone and PC')
