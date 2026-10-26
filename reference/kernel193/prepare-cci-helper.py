from pathlib import Path
import hashlib,json,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel193');out.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
tracked=subprocess.check_output(['git','diff','--name-only'],cwd=k,text=True).splitlines();assert len(tracked)==14
before={p:sha(k/p) for p in tracked}
target=k/'drivers/of/samurai-cci-bringup.c';assert not target.exists();target.write_bytes((ref/target.name).read_bytes())
changes={}
for name,extra in [
 ('drivers/of/Makefile','\nobj-$(CONFIG_OF_SAMURAI_CCI_BRINGUP) += samurai-cci-bringup.o\n'),
 ('drivers/of/Kconfig','\nconfig OF_SAMURAI_CCI_BRINGUP\n\ttristate "Temporary realme X2 Pro CCI1 bringup"\n\tdepends on OF_DYNAMIC && ARCH_QCOM && MODULES\n\thelp\n\t  Reversibly enable only the existing SM8150 CCI1 device on\n\t  realme samurai for camera development. No sensor power writes.\n\t  Keep disabled for normal builds; a static device tree should\n\t  describe the completed camera port.\n')]:
 p=k/name;old=p.read_bytes();(out/(p.name+'-before-private')).write_bytes(old);p.write_bytes(old+extra.encode());changes[name]=dict(before_sha256=hashlib.sha256(old).hexdigest(),after_sha256=sha(p))
assert all(sha(k/p)==digest for p,digest in before.items())
diff=subprocess.check_output(['git','diff','--','drivers/of/Makefile','drivers/of/Kconfig'],cwd=k,text=True)
new=subprocess.run(['git','diff','--no-index','--','/dev/null',str(target)],capture_output=True,text=True);assert new.returncode==1
patch=diff+new.stdout.replace('b'+str(k)+'/', 'b/').replace('a'+str(k)+'/', 'a/')
(ref/'samurai-cci-bringup.patch').write_text(patch)
check=subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','--ignore','FILE_PATH_CHANGES','-'],input=patch,capture_output=True,text=True);(out/'cci-helper-checkpatch-private.log').write_text(check.stdout+check.stderr)
report=dict(stage=193,previous14_source_hashes=before,changes=changes,helper_source_sha256=sha(target),checkpatch_exit=check.returncode,hardware_changes=False)
(ref/'cci-helper-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='previous14_source_hashes'}));print(check.stdout[-2300:])
