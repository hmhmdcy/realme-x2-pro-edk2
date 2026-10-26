"""Install only the new matching sensor module; preserve all existing modules."""
from pathlib import Path
import base64,hashlib,json,shlex
import host
R=Path(__file__).resolve().parent;baseline=json.loads((host.PRIVATE/'deployment-baseline-private.json').read_text())
build=json.loads((R/'current-module-build-validation.json').read_text())
module=(host.PRIVATE/'current-module-build-r3/s5k3m5.ko').read_bytes();assert hashlib.sha256(module).hexdigest()==build['sha256']
data=dict(boot_id=baseline['boot_id'],module_b64=base64.b64encode(module).decode(),sha256=build['sha256'],
 vermagic=build['vermagic'],cci_sha256=baseline['modules']['v4l2_cci']['sha256'],package_db_sha256=baseline['package_db_sha256'])
code=r'''
from pathlib import Path
import base64,hashlib,json,os,shutil,subprocess,sys,traceback
os.umask(0o077);args=json.load(sys.stdin);root=Path('/var/lib/samurai/k270-module-transaction');root.mkdir(mode=0o700)
state=dict(state='preflight',terminal=False,pid=os.getpid());dest=None;added=False;saved={}
def save():(root/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def inventory(tree):return {str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')}
save()
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==args['boot_id']
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 assert not Path('/sys/module/s5k3m5').exists()
 tree=Path('/usr/lib/modules')/os.uname().release
 before=inventory(tree);(root/'modules-before-private.json').write_text(json.dumps(before,indent=2)+'\n')
 cci=Path(subprocess.check_output(['modinfo','-n','v4l2_cci'],text=True).strip());assert sha(cci)==args['cci_sha256']
 dest=tree/'kernel/drivers/media/i2c/s5k3m5.ko';assert not dest.exists()
 assert sha('/lib/apk/db/installed')==args['package_db_sha256']
 backup=root/'before';backup.mkdir(mode=0o700)
 for p in tree.glob('modules.*'):
  if p.is_file() and not p.is_symlink():
   saved[p.name]=dict(mode=p.stat().st_mode&0o777);shutil.copy2(p,backup/p.name)
 (root/'depfiles-before-private.json').write_text(json.dumps(saved,indent=2)+'\n')
 candidate=root/'s5k3m5.ko';candidate.write_bytes(base64.b64decode(args['module_b64']));assert sha(candidate)==args['sha256']
 assert subprocess.check_output(['modinfo','-F','vermagic',str(candidate)],text=True).strip()==args['vermagic']
 assert subprocess.check_output(['modinfo','-F','intree',str(candidate)],text=True).strip()=='Y'
 state['state']='installing-new-module';save();dest.write_bytes(candidate.read_bytes());dest.chmod(0o644);added=True
 subprocess.run(['depmod','-a',os.uname().release],check=True,capture_output=True)
 dry=subprocess.run(['modprobe','-n','-v','s5k3m5'],capture_output=True,text=True,check=True)
 (root/'dependency-dry-run-private.log').write_text(dry.stdout+dry.stderr);assert 's5k3m5.ko' in dry.stdout
 after=inventory(tree);assert set(after)-set(before)=={'kernel/drivers/media/i2c/s5k3m5.ko'}
 assert all(after[name]==value for name,value in before.items())
 assert sha('/lib/apk/db/installed')==args['package_db_sha256'] and not Path('/sys/module/s5k3m5').exists()
 report=dict(stage=270,new_module_staged=True,new_module_sha256=args['sha256'],existing_modules_byte_exact=True,
  old_module_count=len(before),new_module_count=len(after),existing_cci_preserved=True,dependency_dry_run_passed=True,
  package_db_unchanged=True,no_hot_load_or_unload=True,matching_dtb_boot_required=True)
 (root/'summary.json').write_text(json.dumps(report,indent=2)+'\n');os.sync();state.update(state='terminal',terminal=True,exit_code=0);save();print(json.dumps(report))
except BaseException:
 (root/'failure-private.txt').write_text(traceback.format_exc())
 if added:
  dest.unlink()
  for p in tree.glob('modules.*'):
   if p.is_file() and not p.is_symlink() and p.name not in saved:p.unlink()
  for name,row in saved.items():shutil.copy2(root/'before'/name,tree/name)
 state.update(state='failed',terminal=True,exit_code=1);save();raise
'''
q=host.ssh('python3 -c '+shlex.quote(code),input=json.dumps(data).encode(),timeout=40)
(host.PRIVATE/'module-stage-response-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
(R/'module-stage-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
