"""Run old/new actual step bodies with modeled I/O, no real clock wait or phone."""
from pathlib import Path
import hashlib,json,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;AUTHOR=HERE.parent/'charger-reattach-observation-candidate'
R8=HERE.parent/'r8-source-integration/kernel-sources/drivers/power/supply'
OUT=Path('/home/cy122/charging-management-20261023/charge-timer-hold-tests-03')
assert not OUT.exists();OUT.mkdir(mode=0o700)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
prefix=(HERE.parent/'thermal-bands-candidate/test-step.c').read_text().split('int main(void)',1)[0]
prefix=prefix.replace('#include <charge-cycle.h>','#include <charge-cycle.h>\n#include <charge-cycle-hold.h>\n#include <reattach-observation.h>')
prefix=prefix.replace('bool auto_requested, latched, paused, sample_full, source_inhibit;',
                      'bool auto_requested, latched, paused, sample_full, source_inhibit;\n\tbool timer_hold_confirmed;\n\tstruct sm_reattach_observation reattach;')
test=prefix+(HERE/'test-step.inc').read_text()
(OUT/'test.c').write_text(test)
results={}
for label,path in [('baseline',AUTHOR/'samurai-mp2650.c'),('candidate',HERE/'samurai-mp2650.c')]:
    source=path.read_text();start=source.index('static int sm_step_locked(');end=source.index('\n}\n',start)+3
    (OUT/'sm-step-extracted.inc').write_text(source[start:end])
    argv=['cc','-std=c11','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',
          '-DBASELINE='+str(int(label=='baseline')),'-I'+str(HERE),'-I'+str(AUTHOR),'-I'+str(R8),str(OUT/'test.c'),'-o',str(OUT/label)]
    build=subprocess.run(argv,capture_output=True,text=True)
    assert build.returncode==0,build.stderr
    child=subprocess.Popen([str(OUT/label)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout,stderr=child.communicate();assert child.returncode==0,stdout.decode()+stderr.decode()
    results[label]=dict(pid=child.pid,terminal=True,returncode=child.returncode,result=json.loads(stdout),
                        stderr=stderr.decode(),actual_step_sha256=sha(source[start:end].encode()),command=argv)
result=dict(passed=True,scope='old/new actual sm_step_locked, actual policy/core/full/cycle with modeled collection/register/time boundaries',
            tests=results,sources={n:sha((HERE/n).read_bytes()) for n in ['samurai-mp2650.c','charge-cycle-hold.h','test-step.inc','test.py']},
            installed=False,phone_accessed=False,ten_hour_real_cycle_accepted=False,TCA_semantic_compatibility_accepted=False)
with (HERE/'test-result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,results={k:v['result'] for k,v in results.items()})))
