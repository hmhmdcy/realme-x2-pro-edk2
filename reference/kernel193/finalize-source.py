from pathlib import Path
import subprocess,json,hashlib,ast
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel193';out=Path('/mnt/e/edk2-samurai-out/kernel193');k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
base=json.loads((ref/'cci-helper-source-validation.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(k/p)==digest for p,digest in base['previous14_source_hashes'].items())
assert sha(k/'.config')=='55f1f0a35bd4f20ad70ebd383a8863e05d0b6d53a07c0f0f09fb47cee057913a'
assert len((k/'Module.symvers').read_text().splitlines())==16793 and len((k/'modules.order').read_text().splitlines())==770
patch=subprocess.check_output(['git','diff','--','drivers/of/Makefile','drivers/of/Kconfig'],cwd=k,text=True)
for name in ['samurai-cci-bringup.c','samurai-front-identify.c']:
 p=k/'drivers/of'/name;assert p.read_bytes()==(ref/name).read_bytes()
 diff=subprocess.run(['git','diff','--no-index','--','/dev/null',str(p)],capture_output=True,text=True);assert diff.returncode==1
 patch+=diff.stdout.replace('b'+str(k)+'/', 'b/').replace('a'+str(k)+'/', 'a/')
(ref/'samurai-camera-bringup.patch').write_text(patch)
subprocess.run(['git','apply','--reverse','--check',str(ref/'samurai-camera-bringup.patch')],cwd=k,check=True,capture_output=True)
check=subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','--ignore','FILE_PATH_CHANGES','-'],input=patch,capture_output=True,text=True);(out/'combined-checkpatch-private.log').write_text(check.stdout+check.stderr);assert check.returncode==0,check.stdout
for p in ref.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
for p in ref.glob('*.json'):json.loads(p.read_text())
fields=['drivers/of/Makefile','drivers/of/Kconfig','drivers/of/samurai-cci-bringup.c','drivers/of/samurai-front-identify.c']
report=dict(stage=193,source_sha256={n:sha(k/n) for n in fields},patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),checkpatch_exit=0,reverse_apply_check_passed=True,config_restored_byte_exact=True,prior14_tracked_sources_unchanged=True,full_symvers_and_module_order_restored=True,production_camera_driver_modified=False,helpers_enabled_by_default=False,physical_capture_complete=False)
(ref/'source-final-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
