from pathlib import Path
import subprocess,hashlib,json
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel193')
target=k/'drivers/of/samurai-front-identify.c';target.write_bytes((ref/target.name).read_bytes())
diff=subprocess.run(['git','diff','--no-index','--','/dev/null',str(target)],capture_output=True,text=True);assert diff.returncode==1
patch=diff.stdout.replace('b'+str(k)+'/', 'b/').replace('a'+str(k)+'/', 'a/');(ref/'samurai-front-identify.patch').write_text(patch)
check=subprocess.run(['perl',str(k/'scripts/checkpatch.pl'),'--no-tree','--strict','--ignore','FILE_PATH_CHANGES','-'],input=patch,capture_output=True,text=True);(out/'front-helper-checkpatch-private.log').write_text(check.stdout+check.stderr)
report=json.loads((ref/'front-helper-source-validation.json').read_text());report['helper_source_sha256']=hashlib.sha256(target.read_bytes()).hexdigest();report['checkpatch_exit']=check.returncode
(ref/'front-helper-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(check.stdout[-4500:])
