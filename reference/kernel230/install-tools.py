"""Upload only guarded transition tools; the in-tree module is already staged."""
from pathlib import Path
import hashlib,json
import host
ref=Path(__file__).resolve().parent
code="""from pathlib import Path
import json
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k230-baseline/boot-id-private.txt').read_bytes()
assert json.loads((root/'k230-baseline/summary.json').read_text())['default_intree2abde_note_saved']
p=root/'k230-tools';assert not p.exists();p.mkdir(mode=0o700)
print('K230_NEW_TOOLS_DIRECTORY_CREATED')
"""
r=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'tools-create-private.log').write_bytes(r.stdout+r.stderr)
manifest={}
for name in ['quiesce-current183.sh','stop-gnss-idle.py','quiesce-camera.py','disable-crtc.py','check-quiesce.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py','preflight-transition.py']:
    dest='/var/lib/samurai/k230-tools/'+name if name in ['linux-restart2-bootloader.py','preflight-transition.py'] else '/tmp/k230-'+name
    host.upload(ref/name,dest);manifest[dest]=hashlib.sha256((ref/name).read_bytes()).hexdigest()
target=host.PRIVATE/'uploaded-sources-private.json';assert not target.exists();target.write_text(json.dumps(manifest,indent=2)+'\n')
host.upload(target,'/var/lib/samurai/k230-tools/uploaded-sources-private.json')
code="""from pathlib import Path
import hashlib,json,subprocess
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k230-baseline/boot-id-private.txt').read_bytes()
manifest=json.loads((root/'k230-tools/uploaded-sources-private.json').read_text())
for name,digest in manifest.items():
 p=Path(name);assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
 if p.suffix=='.py':compile(p.read_text(),name,'exec')
 elif p.suffix=='.sh':subprocess.run(['sh','-n',str(p)],check=True)
print(json.dumps(dict(stage=230,uploaded_tools=len(manifest),all_exact_paths_and_hashes_verified=True,python_and_shell_syntax=True,module_file_or_live_driver_changed=False)))
"""
r=host.ssh('python3 -',input=code.encode(),timeout=25)
(host.PRIVATE/'tools-check-private.log').write_bytes(r.stdout+r.stderr)
report=json.loads(r.stdout);(ref/'tools-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
