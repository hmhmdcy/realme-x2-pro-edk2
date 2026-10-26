from pathlib import Path
import hashlib,json
import host
R=Path(__file__).resolve().parent
code="""from pathlib import Path
import json
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k233-baseline/boot-id-private.txt').read_bytes()
assert json.loads((root/'k233-module-stage/transaction-state-private.json').read_text())['state']=='verified'
assert (root/'k233-tools').is_dir() and not (root/'k233-tools/uploaded-sources-private.json').exists()
print('FRESH_TOOLS_CONTEXT_VERIFIED')
"""
r=host.ssh('python3 -',input=code.encode(),timeout=15);(host.PRIVATE/'tools-before-private.log').write_bytes(r.stdout+r.stderr)
manifest={}
for name in ['quiesce-current183.sh','stop-gnss-idle.py','quiesce-camera.py','disable-crtc.py','check-quiesce.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py','preflight-transition.py']:
 dest='/var/lib/samurai/k233-tools/'+name if name in ['linux-restart2-bootloader.py','preflight-transition.py'] else '/tmp/k233-'+name
 host.upload(R/name,dest);manifest[dest]=hashlib.sha256((R/name).read_bytes()).hexdigest()
p=host.PRIVATE/'uploaded-sources-private.json';p.write_text(json.dumps(manifest,indent=2)+'\n');host.upload(p,'/var/lib/samurai/k233-tools/uploaded-sources-private.json')
code="""from pathlib import Path
import hashlib,json,subprocess
root=Path('/var/lib/samurai');before=root/'k233-baseline'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(before/'boot-id-private.txt').read_bytes()
for name,digest in json.loads((root/'k233-tools/uploaded-sources-private.json').read_text()).items():
 p=Path(name);assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
 if p.suffix=='.py':compile(p.read_text(),name,'exec')
 else:subprocess.run(['sh','-n',name],check=True)
parts=(before/'partition-check.sha256').read_text().splitlines();assert len(parts)==3
candidate=json.loads((root/'k233-tools/deployment-lock-private.json').read_text())['files']['boot_candidate']['sha256']
assert sum(l.endswith('  /dev/sde11') for l in parts)==1
(root/'k233-tools/partition-after.sha256').write_text(''.join((candidate+'  /dev/sde11' if l.endswith('  /dev/sde11') else l)+'\\n' for l in parts))
assert Path('/sys/module/qcom_pm8008/notes/.note.gnu.build-id').read_bytes()==(before/'mfd-loaded-note-private.bin').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
print(json.dumps(dict(stage=233,uploaded_tools=8,exact_paths_hashes_syntax_verified=True,pre_post_boot_manifests_split=True,old_mfd_still_live=True)))
"""
r=host.ssh('python3 -',input=code.encode(),timeout=25);(host.PRIVATE/'tools-check-private.log').write_bytes(r.stdout+r.stderr)
report=json.loads(r.stdout);(R/'tools-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
