"""Finish validation after the three completed build phases; do not rebuild them."""
from pathlib import Path
import ast,hashlib,json,os,stat,subprocess,sys,tarfile

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel288')
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
COMMIT='8c79b7e1912790d3e18a84c9c6621a6d92baa768'
sys.path.insert(0,str(ROOT.parent/'kernel284'))
from storage import mounted_build
BUILD=mounted_build()
state=json.loads((PRIVATE/'boot-candidate-state-private.json').read_text())
assert state['terminal'] and len(state['phases'])==3 and all(p['exit']==0 for p in state['phases'])
assert state['commit']==COMMIT and not (ROOT/'boot-candidate-build-validation.json').exists()
phases=state['phases']
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
s=(ROOT/'build-boot-candidate.py').read_text()
tree=ast.parse(s)
snapshot_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='snapshot')
exec(compile(ast.Module(body=[snapshot_node],type_ignores=[]),str(ROOT/'build-boot-candidate.py'),'exec'),globals())
payload=BUILD.parent/'input-initramfs288'
original=Path('/home/cy122/pmos-samurai-kernel136/initramfs')
payload_manifest=json.loads((PRIVATE/'boot-initramfs-manifest-private.json').read_text())
assert snapshot(payload)==payload_manifest
current_original=snapshot(original)
module_changes=['lib/modules/samurai/'+n+'.ko' for n in ['btbcm','btqca','hci_uart']]
assert set(current_original)==set(payload_manifest)
assert {n for n in current_original if current_original[n]!=payload_manifest[n]}==set(module_changes)
module_root=BUILD.parent/'modules288'
release=(BUILD/'include/config/kernel.release').read_text().strip()
stage=module_root/'lib/modules'/release
for n in module_changes:
    found=list(stage.rglob(Path(n).name));assert len(found)==1
    assert (payload/n).read_bytes()==found[0].read_bytes(),n
before=(PRIVATE/'completed-compile-pix288/.config').read_text()
start=s.index('def config_map(')
exec(compile(s[start:],str(ROOT/'build-boot-candidate.py'),'exec'),globals())
