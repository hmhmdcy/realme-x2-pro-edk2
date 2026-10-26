from pathlib import Path
import json,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel156')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel156')
before=json.loads((out/'source-before-private.json').read_text())
for n,s in before.items():
    if s is None:assert not (k/n).exists(),n
    else:assert (k/n).read_text()==s,n
assert not (out/'source-before-style2-failed-private.json').exists()
(out/'source-before-private.json').rename(out/'source-before-style2-failed-private.json')
(out/'other-diff-before-private.patch').rename(out/'other-diff-before-style2-failed-private.patch')
subprocess.run(['python3',str(ref/'prepare-first-frame.py')],check=True)
