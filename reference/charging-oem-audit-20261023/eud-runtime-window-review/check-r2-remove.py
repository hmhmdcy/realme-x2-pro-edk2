"""Run only the known late-RX removal counterexample against frozen EUD R2."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

HERE=Path(__file__).resolve().parent
R2=HERE.parents[1]/'charging-session-20261023/eud-runtime-window-candidate-r2'
OLD=HERE/'late-remove-counterexample'
OUT=HERE/'r2-late-remove-check';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
delivery=json.loads((R2/'delivery-result.json').read_text())
for name,digest in delivery['frozen_files'].items():assert sha(R2/name)==digest
source=(R2/'eud.c').read_text()
def body(text,name):
    m=re.search(r'^static void '+name+r'\([^;]*?\)\n\{',text,re.M);assert m
    return text[m.start():text.index('\n}',m.end())+2]
inc=(OLD/'candidate-functions.inc').read_text()
old=body(inc,'eud_remove_locked');new=body(source,'eud_remove_locked')
assert inc.count(old)==1 and old!=new
inc=inc.replace(old,new)
(OUT/'candidate-functions.inc').write_text(inc)
for name in ['fake-eud-os.h','nbcon-functions.inc']:(OUT/name).write_bytes((OLD/name).read_bytes())
fixture=(OLD/'test-late-remove.c').read_text().replace('assert(up.rx_work.work.pending==1);','assert(up.rx_work.work.pending==0);')
fixture=fixture.replace('\\"reproduced\\":true','\\"r1_counterexample_closed\\":true').replace('\\"late_rx_pending_after_remove\\":true','\\"late_rx_pending_after_remove\\":false')
(OUT/'test-r2-remove.c').write_text(fixture)
flags=['-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-function','-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread']
build=subprocess.run(['gcc',*flags,str(OUT/'test-r2-remove.c'),'-o',str(OUT/'test-r2-remove')],capture_output=True,text=True)
assert build.returncode==0,build.stderr
run=subprocess.run([str(OUT/'test-r2-remove')],capture_output=True,text=True,timeout=15)
assert run.returncode==0 and not run.stderr,(run.returncode,run.stdout,run.stderr)
for name,digest in delivery['frozen_files'].items():assert sha(R2/name)==digest
result=dict(passed=True,case=json.loads(run.stdout),r2_source_sha256=sha(R2/'eud.c'),
    r2_delivery_sha256=sha(R2/'delivery-result.json'),actual_remove_function_sha256=hashlib.sha256(new.encode()).hexdigest(),
    other_actual_functions_unchanged=True,old_9_and_5_not_rerun=True,author_files_modified=False,
    fake_boundary='same previously reproduced late console enqueue; only actual remove body replaced with frozen R2',
    files={n:sha(OUT/n) for n in ['candidate-functions.inc','fake-eud-os.h','nbcon-functions.inc','test-r2-remove.c']},
    phone_accessed=False,ssh_executed=False,sdk_invoked=False)
(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
