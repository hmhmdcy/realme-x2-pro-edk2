"""Compile and run real driver function bodies against timer/IRQ API stubs."""
from pathlib import Path
import hashlib,json,subprocess
O=Path('/mnt/e/edk2-samurai-out/kernel87');R=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel87');K=Path('/home/cy122/x2pro-linux/linux')
def extract(s,needle):
    a=s.index(needle);b=s.index('{',a);depth=1;c=b+1
    while depth:
        if s[c]=='{':depth+=1
        elif s[c]=='}':depth-=1
        c+=1
    return s[a:c]+'\n'
results={}
for variant,p in [('baseline',O/'dpu_encoder-before.c'),('patched',K/'drivers/gpu/drm/msm/disp/dpu1/dpu_encoder.c')]:
    test=O/('test-'+variant);test.mkdir(exist_ok=True)
    source=p.read_text();bodies='\n'.join(extract(source,n) for n in ['void dpu_encoder_frame_done_callback(',
       'void dpu_encoder_start_frame_done_timer(','static void dpu_encoder_frame_done_timeout('])
    (test/'watchdog-functions.inc').write_text(bodies);(test/'test.c').write_bytes((R/'test-watchdog.c').read_bytes())
    compile_result=subprocess.run(['gcc','-std=gnu11','-O2','-g','-Wall','-Wextra','-o',str(test/'test'),str(test/'test.c')],text=True,capture_output=True)
    (test/'compile.log').write_text(compile_result.stdout+compile_result.stderr);assert compile_result.returncode==0
    run=subprocess.run([str(test/'test')],capture_output=True,text=True)
    (test/'run.log').write_text(run.stdout+run.stderr)
    if variant=='baseline':assert run.returncode==1 and 'post-completion arm must remain inactive' in run.stderr
    else:assert run.returncode==0 and run.stdout.count('PASS ')==6
    results[variant]={'exit':run.returncode,'output':run.stdout+run.stderr,
        'extracted_functions_sha256':hashlib.sha256(bodies.encode()).hexdigest(),
        'compile_log_sha256':hashlib.sha256((test/'compile.log').read_bytes()).hexdigest()}
(O/'watchdog-test-results.json').write_text(json.dumps({'audit':'PASS','scope':'actual function bodies, deterministic timer/IRQ API interleavings; not SMP or hardware',
 'results':results},indent=2)+'\n');print(json.dumps(results,indent=2))
