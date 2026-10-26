"""Narrow offline R2, preserving the entire frozen R1 leaf unchanged."""
from pathlib import Path
import ast,difflib,hashlib,json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'eud-postboot-readonly-candidate'
COMMON=HERE.parent/'apsd-usbin-init-host-operator-r2/common.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(OLD/'device.py')=='8850cf7a9782a13f1d9ea2d6ec672f9d59fffa4c4edf1de970486c8f5b6f6cda'
assert sha(COMMON)=='5c737abf3a5d23d71260dd4c49048191615ca5f1436ac49ea18282f8ccd17c38'
before={p.name:sha(p) for p in OLD.iterdir() if p.is_file()}
for name in ['device-body.py','payload.py','prepare.py','contract.json']:
 assert not (HERE/name).exists(),name
 shutil.copy2(OLD/name,HERE/name)
common=COMMON.read_text()
fn=next(n for n in ast.parse(common).body if isinstance(n,ast.FunctionDef) and n.name=='healthy')
assigns={n.targets[0].id:ast.get_source_segment(common,n) for n in ast.walk(fn)
         if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)
         and n.targets[0].id in ['full','mode']}
assert set(assigns)=={'full','mode'}
fragment='\n'.join(assigns[n] for n in ['full','mode'])+'\n'
(HERE/'healthy-mode-source.inc').write_text(fragment)
helper='def healthy_charge_mode(s):\n'+''.join(' '+line+'\n' for line in fragment.splitlines())+' return bool(mode)\n\n'
body=(HERE/'device-body.py').read_text()
assert body.count('def check_charging(r):')==1
body=body.replace('def check_charging(r):',helper+'def check_charging(r):',1)
marker="  if t['logical_full']:\n"
assert body.count(marker)==1
body=body.replace(marker,"  assert healthy_charge_mode(t),'inconsistent Full/normal state'\n"+marker,1)
(HERE/'device-body.py').write_text(body,newline='\n')
subprocess.run([sys.executable,'-B',str(HERE/'prepare.py')],check=True,capture_output=True)
(HERE/'r1-to-r2.patch').write_text(''.join(difflib.unified_diff((OLD/'device.py').read_text().splitlines(True),
 (HERE/'device.py').read_text().splitlines(True),fromfile='r1/device.py',tofile='r2/device.py')),newline='\n')
assert all(sha(OLD/n)==digest for n,digest in before.items())
result=dict(offline_only=True,R1_unchanged=True,R1_files=before,
 common_source=str(COMMON),common_sha256=sha(COMMON),
 full_mode_source_sha256=sha(HERE/'healthy-mode-source.inc'),
 base_device_sha256=before['device.py'],device_sha256=sha(HERE/'device.py'),
 base_test_receipt_sha256=before['test-result.json'],old_groups_not_rerun=True,
 scope='reuse actual common.healthy Full/normal predicate; no device or existing suite execution')
(HERE/'revision-source-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(device_sha256=result['device_sha256'],R1_unchanged=True)))
