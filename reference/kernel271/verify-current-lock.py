"""Read back the installed payloads and loaded notes against the newly reconciled lock."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
d=json.loads((R.parents[1]/'linux-port/camera/deployment-lock.json').read_text())
expected=dict(packages=d['installed_package_payloads'],modules=d['kernel_modules'])
code=r'''
from pathlib import Path
import hashlib,json,os,stat,struct,subprocess
expected=__EXPECTED__
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k270-work/boot-id-private.txt').read_bytes()
db={}
for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 names=[l[2:] for l in block.splitlines() if l.startswith('P:')]
 if names:db[names[0]]=block
files=0
for pkg in expected['packages']:
 assert 'V:'+pkg['version'] in db[pkg['name']].splitlines()
 for name,item in pkg['files'].items():
  p=Path('/')/name
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert not p.is_symlink() and sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
  files+=1
modules={}
for name,item in expected['modules'].items():
 p=Path(subprocess.check_output(['modinfo','-F','filename',name],text=True).strip());assert sha(p)==item['sha256']
 raw=p.read_bytes();off=struct.unpack_from('<Q',raw,40)[0];size,count,strings=struct.unpack_from('<HHH',raw,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*size) for i in range(count)]
 s=sections[strings];names=raw[s[4]:s[4]+s[5]]
 note=next(raw[x[4]:x[4]+x[5]] for x in sections if names[x[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
 assert Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()==note
 modules[name]=dict(sha256=sha(p),loaded_note_matches_disk=True)
node=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='s5k3m5 8-002d')
controls=subprocess.check_output(['v4l2-ctl','-d',node,'--list-ctrls'],text=True)
assert 'min=32 max=512 step=1 default=32' in next(l for l in controls.splitlines() if 'analogue_gain' in l)
assert 'test_pattern: 0' in subprocess.check_output(['v4l2-ctl','-d',node,'--get-ctrl=test_pattern'],text=True)
report=dict(stage=271,installed_package_count=len(db),seven_runtime_packages_verified=True,payload_records_verified=files,
 modules=modules,native_gain_code_control_verified=True,physical_sensor_pattern_off=True)
print(json.dumps(report))
'''.replace('__EXPECTED__',repr(expected))
q=host.ssh('python3 -',input=code.encode(),timeout=35,check=False)
(host.PRIVATE/'current-lock-response-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and q.stdout,'Inspect read-back discrepancy before further changes'
d=json.loads(q.stdout);(R/'current-lock-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
