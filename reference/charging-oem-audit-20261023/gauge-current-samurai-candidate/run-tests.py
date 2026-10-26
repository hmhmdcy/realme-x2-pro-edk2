from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
OUT=Path('/home/cy122/charging-management-20261023/gauge-current-samurai-tests');OUT.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run(['python3',str(HERE/'prepare-tests.py')],check=True)
flags=['-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
binary=OUT/'test-current';p=subprocess.run(['gcc',*flags,str(HERE/'test-current.c'),'-o',str(binary)],capture_output=True,text=True);assert p.returncode==0,p.stderr
p=subprocess.run([str(binary)],capture_output=True,text=True);assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
groups=[s[4:] for s in p.stdout.splitlines() if s.startswith('ok: ')];assert len(groups)==6 and not p.stderr
r=dict(passed=True,groups=groups,group_count=6,actual_functions=9,original_function_differential_cases=36,asan_ubsan=True,flags=flags,
 stdout=p.stdout,stderr=p.stderr,files={n:sha(HERE/n) for n in ['bq27xxx_battery.c','prepare-tests.py','tested-functions.inc','tested-declarations.inc','function-manifest.json','test-current.c','run-tests.py']},
 hardware_and_OF_fake=True,full_concurrency_proof=False,old_charging_protection_suites_rerun=False,phone_accessed=False,SDK_invoked=False)
(HERE/'test-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(passed=True,groups=6,actual_functions=9,default_differential=36)))
