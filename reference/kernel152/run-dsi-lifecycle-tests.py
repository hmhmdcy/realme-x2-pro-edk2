from pathlib import Path
import hashlib,json,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel152')
out=Path('/mnt/e/edk2-samurai-out/kernel152')
functions=['dsi_ctrl_disable','dsi_sw_reset','dsi_op_mode_config','dsi_err_worker','dsi_host_transfer',
    'msm_dsi_host_disable_irq','msm_dsi_host_enable','msm_dsi_host_disable','msm_dsi_host_power_off']

def extract(s,name):
    import re
    m=re.search(r'^(?:static )?(?:ssize_t|int|void) '+name+r'\([^;]+?\n\{',s,re.M)
    assert m,name
    end=m.end();depth=1
    while depth:
        if s[end]=='{':depth+=1
        elif s[end]=='}':depth-=1
        end+=1
    return s[m.start():end]+'\n'

results=[]
for label,path in [('baseline147',out/'dsi_host.c.before147-private'),
    ('candidate152',k/'drivers/gpu/drm/msm/dsi/dsi_host.c')]:
    d=out/('tests-'+label);d.mkdir(exist_ok=True)
    s=path.read_text()
    (d/'actual-dsi-functions.h').write_text('\n'.join(extract(s,n) for n in functions))
    for sanitizer in [False,True]:
        exe=d/('sanitized' if sanitizer else 'plain')
        cmd=['cc','-std=gnu11','-pthread','-Wall','-Wextra','-Werror','-g','-I'+str(d),
            str(ref/'test-dsi-lifecycle.c'),'-o',str(exe)]
        if sanitizer:cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
        subprocess.run(cmd,check=True)
        r=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
        (d/(exe.name+'.log')).write_text(r.stdout+r.stderr)
        failures=[line.split()[1] for line in r.stdout.splitlines() if line.endswith('FAIL')]
        results.append(dict(label=label,sanitizer=sanitizer,exit=r.returncode,
            cases=sum(line.startswith('CASE ') for line in r.stdout.splitlines()),failures=failures,
            source_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        assert not r.stderr,r.stderr
        if label=='baseline147':
            assert len(failures)==7 and r.returncode==1, r.stdout
        else:assert r.returncode==0 and not failures,r.stdout
report=dict(stage=152,actual_functions=functions,results=results,
    mmio_and_irq_scheduler_are_stubs=True,hardware_timing_verified=False)
(ref/'actual-function-test-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
