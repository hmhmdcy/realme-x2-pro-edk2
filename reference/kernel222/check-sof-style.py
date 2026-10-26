from pathlib import Path
import hashlib,json,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel222');kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel')
p=private/'sof-checkpatch-private.log'
backup=private/'sof-checkpatch-second-description-warning-private.log';assert not backup.exists();backup.write_bytes(p.read_bytes())
check=subprocess.run(['perl',str(kernel/'scripts/checkpatch.pl'),'--no-tree','--no-signoff',str(here/'camss-sm8150-sof-candidate.patch')],capture_output=True);p.write_bytes(check.stdout+check.stderr);assert check.returncode==0
path=here/'sof-candidate-source-validation.json';r=json.loads(path.read_text());r['patch_sha256']=hashlib.sha256((here/'camss-sm8150-sof-candidate.patch').read_bytes()).hexdigest();path.write_text(json.dumps(r,indent=2)+'\n')
path=here/'sof-candidate-build-validation.json';r=json.loads(path.read_text());r.update(checkpatch_exit=0,only_commit_description_wrapped_after_build=True);path.write_text(json.dumps(r,indent=2)+'\n');print('SOF_CANDIDATE_CHECKPATCH_CLEAN_SOURCE_UNCHANGED')
