from pathlib import Path
import host,json
code=r'''
from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
records=[]
for entry in Path('/lib/apk/db/installed').read_text().split('\n\n'):
    lines=entry.splitlines();fields={line[0]:line[2:] for line in lines if len(line)>1 and line[1]==':' and line[0] in ['P','V','D','p','i','o','L','U','T']}
    if fields.get('P','').startswith('libcamera'):
        paths=subprocess.check_output(['apk','info','-L',fields['P']],text=True).splitlines()[1:]
        records.append(dict(metadata=fields,files=[p for p in paths if p]))
print(json.dumps(dict(stage=213,installed_camera_packages=records,staged_files=[str(p.relative_to('/run/samurai-camera213-lut')) for p in Path('/run/samurai-camera213-lut').rglob('*') if p.is_file() and not p.is_symlink() and not p.suffix=='.h'])))
'''
p=host.ssh('python3 -',input=code.encode());report=json.loads(p.stdout)
(Path(__file__).resolve().parent/'camera-packaging-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
