from pathlib import Path
import hashlib
import json
import subprocess

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).resolve().parent
path = k / 'drivers/misc/fastrpc.c'
data = path.read_text()
assert hashlib.sha256(path.read_bytes()).hexdigest() == '952b9664d61e221563f1128f0ff0e3cf0663cfc9f3ab7b55569e2966d8293b54'
for text in ['cctx->vmperms, cctx->vmcount);', 'cctx->reserved_pool_size,', '&cctx->reserved_pool_perms, &perm, 1);']:
    old = '\t\t\t\t ' + text
    assert data.count(old) == 1
    data = data.replace(old, '\t\t\t\t  ' + text)
path.write_text(data)
patch = ref / 'fastrpc-reserved-pool-lifecycle.patch'
header = patch.read_text().split('diff --git ', 1)[0]
diff = subprocess.check_output(['git', 'diff', '--', 'drivers/misc/fastrpc.c'], cwd=k, text=True)
patch.write_text(header + diff)
p = subprocess.run(['perl', 'scripts/checkpatch.pl', '--no-signoff', '--strict', str(patch)], cwd=k, capture_output=True)
Path('/mnt/e/edk2-samurai-out/kernel186/fastrpc-checkpatch-r2-private.log').write_bytes(p.stdout + p.stderr)
report = json.loads((ref / 'fastrpc-source-validation.json').read_text())
report['source_after_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
report['checkpatch_exit'] = p.returncode
report['initial_alignment_check_failure_preserved'] = True
(ref / 'fastrpc-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
if p.returncode:
    print(p.stdout.decode(errors='replace'))
    raise SystemExit(p.returncode)
