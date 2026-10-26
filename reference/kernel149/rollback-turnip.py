"""Restore only the original library belonging to this recorded deployment."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
out=Path('/var/lib/samurai/k149-deployment')
m=json.loads((out/'deployment.json').read_text())
target=Path('/usr/lib/libvulkan_freedreno.so');backup=out/'libvulkan_freedreno.so.original'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(target)==m['candidate_sha256'] and digest(backup)==m['original_sha256']
temp=target.with_name('.libvulkan_freedreno.so.k149-restore');assert not temp.exists()
shutil.copy2(backup,temp)
with temp.open('rb') as f:os.fsync(f.fileno())
temp.replace(target)
assert digest(target)==m['original_sha256']
subprocess.run(['sync'],check=True)
print(json.dumps(dict(rollback_complete=True,original_sha256=m['original_sha256'])))
