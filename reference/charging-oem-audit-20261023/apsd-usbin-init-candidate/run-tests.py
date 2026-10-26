from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run(['python3',str(HERE/'prepare-tests.py')],check=True)
flags=['-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer']
b=subprocess.run(['gcc',*flags,str(HERE/'test-init.c'),'-o',str(HERE/'test-init')],capture_output=True,text=True)
assert b.returncode==0,b.stderr
p=subprocess.run([str(HERE/'test-init')],capture_output=True,text=True)
assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
cases=[l[4:] for l in p.stdout.splitlines() if l.startswith('ok: ')]
assert len(cases)==12 and not p.stderr
state=json.loads(next(l[7:] for l in p.stdout.splitlines() if l.startswith('state: ')))
assert state['schema']==1 and state['running'] and state['armed'] and state['remaining_ms']==60000 and not state['can_unload']
r=dict(passed=True,groups=cases,group_count=12,actual_module_functions=12,actual_core_functions=7,
 flags=flags,state_schema_fixture=state,runtime_stdout=p.stdout,runtime_stderr=p.stderr,
 files={n:sha(HERE/n) for n in ['samurai-usbin-init.c','usbin-init-core.h','test-init.c','tested-functions.inc','tested-struct.inc','function-manifest.json','prepare-tests.py','run-tests.py']},
 phone_accessed=False,ssh_executed=False,usb_accessed=False,sdk_invoked=False,
 scope='actual core/control/worker/ref/PM-stop and fixed regmap IO functions; fake hardware/OS; no physical off guarantee between reads')
(HERE/'test-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'groups':12}))
