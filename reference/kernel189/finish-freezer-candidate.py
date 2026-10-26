from pathlib import Path
import difflib,hashlib,json,shutil,subprocess

k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/kernel189');path=k/'drivers/misc/fastrpc.c'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='53b4896612b299e7de7970402a9304753c6ee20f54f0741b33dc1ff784761827'
text=path.read_text().replace('\t\t\t\t\t\tTASK_INTERRUPTIBLE | TASK_FREEZABLE);','\t\t\t\t\t\t\tTASK_INTERRUPTIBLE | TASK_FREEZABLE);')
path.write_text(text)
raw=(private/'fastrpc-original-private.c').read_text()
patch=''.join(difflib.unified_diff(raw.splitlines(True),text.splitlines(True),fromfile='a/drivers/misc/fastrpc.c',tofile='b/drivers/misc/fastrpc.c'))
(ref/'fastrpc-freezer-wait.patch').write_text(patch)
old=ref/'fastrpc-source-validation.json'
failure=ref/'fastrpc-source-r1-style-failure-validation.json';assert not failure.exists();shutil.copyfile(old,failure)
p=subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff','--ignore','COMMIT_MESSAGE',str(ref/'fastrpc-freezer-wait.patch')],cwd=k,capture_output=True)
(private/'checkpatch-r2-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(old.read_text());report.update(source_after_sha256=hashlib.sha256(text.encode()).hexdigest(),checkpatch_exit=p.returncode,
 local_diff_checked_without_mail_commit_message=True)
old.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report));print(p.stdout.decode());assert p.returncode==0
