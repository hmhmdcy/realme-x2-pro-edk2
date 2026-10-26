"""Atomic disk staging with automatic file rollback; never reload live PMICs."""
from pathlib import Path
import hashlib,json,os,stat,struct,subprocess,tempfile
os.umask(0o077)
root=Path('/var/lib/samurai');before=root/'k233-baseline';out=root/'k233-module-stage';tools=root/'k233-tools'
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(before/'boot-id-private.txt').read_bytes()
assert not out.exists() and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
sha=lambda b:hashlib.sha256(b).hexdigest()
lock=json.loads((tools/'deployment-lock-private.json').read_text())
tree=Path('/usr/lib/modules')/os.uname().release
old_rel='kernel/drivers/mfd/qcom-pm8008.ko';new_rel='kernel/drivers/reset/reset-realme-rmx1931-pm8008.ko'
target=tree/old_rel;provider=tree/new_rel;config=Path('/etc/modprobe.d/samurai-pmic-bringup.conf')
assert not config.exists() and not provider.exists()
original=target.read_bytes();assert original==(before/'mfd-original-private.ko').read_bytes()
old_note=(before/'mfd-loaded-note-private.bin').read_bytes();loaded=Path('/sys/module/qcom_pm8008/notes/.note.gnu.build-id')
assert loaded.read_bytes()==old_note and not Path('/sys/module/reset_realme_rmx1931_pm8008').exists()
assert not Path('/sys/module/qcom_pm8008/parameters/experimental_p_address_only').exists()
inventory=json.loads((before/'module-inventory-private.json').read_text())
def inventory_now():return {str(f.relative_to(tree)):sha(f.read_bytes()) for f in tree.rglob('*') if f.is_file()}
assert inventory_now()==inventory
loader_before=json.loads((before/'loader-config-before-private.json').read_text())
assert all(sha(Path(n).read_bytes())==v for n,v in loader_before.items())
candidates={old_rel:tools/'qcom-pm8008.ko',new_rel:tools/'reset-realme-rmx1931-pm8008.ko'}
expected={old_rel:lock['files']['mfd_module']['sha256'],new_rel:lock['files']['provider_module']['sha256']}
old_vm=subprocess.check_output(['modinfo','-F','vermagic',str(target)],text=True).strip()
for name,f in candidates.items():
 assert sha(f.read_bytes())==expected[name]
 assert subprocess.check_output(['modinfo','-F','vermagic',str(f)],text=True).strip()==old_vm
 assert subprocess.check_output(['modinfo','-F','intree',str(f)],text=True).strip()=='Y'
out.mkdir(mode=0o700);(out/'boot-id-private.txt').write_bytes(boot);(out/'mfd-original-private.ko').write_bytes(original)
metadata=json.loads((before/'module-metadata-meta-private.json').read_text());old_meta=target.stat()
state_path=out/'transaction-state-private.json'
def sync_directory(path):
 fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def atomic(path,data,mode=0o644,uid=0,gid=0):
 fd,name=tempfile.mkstemp(prefix='.'+path.name+'.k233-',dir=path.parent);temp=Path(name)
 try:
  try:
   with os.fdopen(fd,'wb',closefd=False) as f:f.write(data);f.flush()
   os.fchmod(fd,mode);os.fchown(fd,uid,gid);os.fsync(fd)
  finally:os.close(fd)
  assert temp.read_bytes()==data;os.replace(temp,path);sync_directory(path.parent)
 finally:
  if temp.exists():temp.unlink()
def state(phase,**fields):
 atomic(state_path,(json.dumps(dict(stage=233,state=phase,runtime_reloaded=False,transition_sent=False,**fields))+'\n').encode(),0o600)
state('prepared')
try:
 # udev starts earlier than the modules OpenRC service; kmod must see both here.
 configuration=b'options qcom_pm8008 experimental_p_address_only=1\nsoftdep qcom_pm8008 pre: reset_realme_rmx1931_pm8008\n'
 atomic(config,configuration);state('loader_config_installed')
 atomic(provider,candidates[new_rel].read_bytes())
 atomic(target,candidates[old_rel].read_bytes(),stat.S_IMODE(old_meta.st_mode),old_meta.st_uid,old_meta.st_gid)
 state('module_files_installed')
 result=subprocess.run(['depmod','-a',os.uname().release],capture_output=True,timeout=45)
 (out/'depmod-private.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0
 state('depmod_complete')
 # -D is installed kmod's query-only mode; it does not insert a module.
 result=subprocess.run(['modprobe','--show-depends','qcom_pm8008'],capture_output=True,timeout=15)
 (out/'kmod-plan-private.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0
 plan=result.stdout.decode();lines=[l for l in plan.splitlines() if l.startswith('insmod ')]
 assert len(lines)==2 and 'reset-realme-rmx1931-pm8008.ko' in lines[0] and 'qcom-pm8008.ko' in lines[1]
 assert 'experimental_p_address_only=1' in lines[1]
 actual=inventory_now();ko={n:v for n,v in actual.items() if n.endswith('.ko')}
 wanted={n:v for n,v in inventory.items() if n.endswith('.ko')};wanted.update(expected)
 assert ko==wanted and len(ko)==773
 assert all(sha(Path(n).read_bytes())==v for n,v in loader_before.items()) and config.read_bytes()==configuration
 assert loaded.read_bytes()==old_note and not Path('/sys/module/reset_realme_rmx1931_pm8008').exists()
 assert Path('/lib/apk/db/installed').read_bytes()==(before/'installed-before-private.txt').read_bytes()
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot
 (out/'module-inventory-after-private.json').write_text(json.dumps(actual,indent=2)+'\n')
 (out/'module-tree-after.sha256').write_text(''.join(v+'  '+n+'\n' for n,v in sorted(actual.items())))
 loader_after=dict(loader_before);loader_after[str(config)]=sha(configuration)
 (out/'loader-config-after.sha256').write_text(''.join(v+'  '+n+'\n' for n,v in sorted(loader_after.items())))
 state('verified',old_mfd_still_loaded=True)
except BaseException as original_error:
 # Recovery must not depend on being able to write the diagnostic journal.
 try:state('rolling_back_files')
 except BaseException:pass
 assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot and loaded.read_bytes()==old_note
 rollback_errors=[]
 def restore(operation):
  try:operation()
  except BaseException as error:rollback_errors.append(type(error).__name__)
 restore(lambda:atomic(target,original,stat.S_IMODE(old_meta.st_mode),old_meta.st_uid,old_meta.st_gid))
 def remove_own(path):
  if path.exists():path.unlink();sync_directory(path.parent)
 restore(lambda:remove_own(provider));restore(lambda:remove_own(config))
 for f in tree.rglob('*'):
  if f.is_file() and not f.name.endswith('.ko') and str(f.relative_to(tree)) not in inventory:restore(lambda f=f:f.unlink())
 for n,meta in metadata.items():restore(lambda n=n,meta=meta:atomic(tree/n,(before/'module-metadata-before'/n).read_bytes(),meta['mode'],meta['uid'],meta['gid']))
 restore(lambda:sync_directory(tree))
 assert not rollback_errors and inventory_now()==inventory,('Rollback requires inspection',rollback_errors)
 assert loaded.read_bytes()==old_note and not Path('/sys/module/reset_realme_rmx1931_pm8008').exists()
 assert not config.exists() and all(sha(Path(n).read_bytes())==v for n,v in loader_before.items())
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot
 try:state('rolled_back_files',old_mfd_still_loaded=True)
 except BaseException:pass
 raise
report=dict(stage=233,two_module_files_staged=True,ko_count=773,module_related_file_count=len(actual),
 old_mfd_runtime_note_unchanged=True,provider_not_loaded=True,kmod_query_order_provider_then_mfd=True,
 preload_option_verified=True,unrelated_ko_unchanged=True,old_loader_configs_unchanged=True,
 package_database_unchanged=True,taint=0,no_reload_or_transition=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
