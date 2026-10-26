from pathlib import Path
import hashlib,json,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel156')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel156')
report=json.loads((ref/'source-validation.json').read_text())
before=json.loads((out/'source-before-private.json').read_text())
for n,sha in report['after_sha256'].items():assert hashlib.sha256((k/n).read_bytes()).hexdigest()==sha,n
assert not (out/'source-after-v1-private.json').exists()
(out/'source-after-v1-private.json').write_text(json.dumps({n:(k/n).read_text() for n in report['modified_files']}))
(out/'source-v1-validation.json').write_text(json.dumps(report,indent=2))
(out/'first-frame-backlight-v1.patch').write_bytes((ref/'first-frame-backlight.patch').read_bytes())
(out/'source-before-private.json').rename(out/'source-before-v1-private.json')
(out/'other-diff-before-private.patch').rename(out/'other-diff-before-v1-private.patch')
for n,s in before.items():
    if s is None:(k/n).unlink()
    else:(k/n).write_text(s)
subprocess.run(['python3',str(ref/'prepare-first-frame.py')],check=True)
