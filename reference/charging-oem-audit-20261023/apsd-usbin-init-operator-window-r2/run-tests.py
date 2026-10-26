from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-usbin-init-candidate'
OUT=Path('/home/cy122/charging-management-20261023/apsd-usbin-init-operator-window-r2-tests');OUT.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert (HERE/'samurai-usbin-init.c').read_bytes()==(OLD/'samurai-usbin-init.c').read_bytes()
assert (HERE/'usbin-init-core.h').read_bytes()==(OLD/'usbin-init-core.h').read_bytes().replace(b'#define UI_WAIT_MS 60000ULL',b'#define UI_WAIT_MS 300000ULL')
subprocess.run(['python3',str(HERE/'prepare-tests.py')],check=True)
for n in ['tested-functions.inc','tested-struct.inc','function-manifest.json']:assert sha(HERE/n)==sha(OLD/n),n
flags=['-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
binary=OUT/'test-boundary';p=subprocess.run(['gcc',*flags,str(HERE/'test-boundary.c'),'-o',str(binary)],capture_output=True,text=True)
assert p.returncode==0,p.stderr
p=subprocess.run([str(binary)],capture_output=True,text=True);assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
groups=[s[4:] for s in p.stdout.splitlines() if s.startswith('ok: ')];assert len(groups)==5 and not p.stderr
fixtures={}
for line in p.stdout.splitlines():
 if line.startswith('fixture:'):
  name,value=line[8:].split(' ',1);fixtures[name]=json.loads(value)
assert fixtures['armed']['remaining_ms']==300000
assert fixtures['waiting_after_61s']['remaining_ms']==239000
assert fixtures['clear_verified']['prewrite_boottime_ms']==62750
(HERE/'actual-state-fixtures.json').write_text(json.dumps(fixtures,indent=2)+'\n')
(HERE/'actual-state-fixtures.jsonl').write_text('\n'.join(json.dumps(dict(name=n,state=s)) for n,s in fixtures.items())+'\n')
r=dict(passed=True,group_count=5,groups=groups,flags=flags,asan_ubsan=True,actual_module_functions=12,actual_core_functions=7,
 stdout=p.stdout,stderr=p.stderr,window_ms=300000,fixtures_from_actual_state_show=True,
 old_12_receipt_sha256=sha(OLD/'test-result.json'),old_12_rerun=False,
 files={n:sha(HERE/n) for n in ['samurai-usbin-init.c','usbin-init-core.h','prepare-tests.py','test-boundary-prefix.inc','test-boundary.c','tested-functions.inc','tested-struct.inc','function-manifest.json','actual-state-fixtures.json','actual-state-fixtures.jsonl','run-tests.py']},
 phone_accessed=False,sdk_invoked=False,hardware_test=False)
(HERE/'test-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(passed=True,groups=5,window_ms=300000)))
