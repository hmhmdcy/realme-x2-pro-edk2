from pathlib import Path
import subprocess,hashlib,json
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel193')
report=json.loads((ref/'cci-helper-source-validation.json').read_text());target=k/'drivers/of/samurai-cci-bringup.c';target.write_bytes((ref/target.name).read_bytes())
assert all(hashlib.sha256((k/p).read_bytes()).hexdigest()==digest for p,digest in report['previous14_source_hashes'].items())
diff=subprocess.check_output(['git','diff','--','drivers/of/Makefile','drivers/of/Kconfig'],cwd=k,text=True)
new=subprocess.run(['git','diff','--no-index','--','/dev/null',str(target)],capture_output=True,text=True);assert new.returncode==1
patch=diff+new.stdout.replace('b'+str(k)+'/', 'b/').replace('a'+str(k)+'/', 'a/');(ref/'samurai-cci-bringup.patch').write_text(patch)
check=subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','--ignore','FILE_PATH_CHANGES','-'],input=patch,capture_output=True,text=True);(out/'cci-helper-checkpatch-private.log').write_text(check.stdout+check.stderr)
report['helper_source_sha256']=hashlib.sha256(target.read_bytes()).hexdigest();report['checkpatch_exit']=check.returncode
(ref/'cci-helper-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(check.stdout[-1200:]);assert check.returncode==0
