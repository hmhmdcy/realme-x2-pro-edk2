from pathlib import Path
import hashlib,json,re,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel154')
out=Path('/mnt/e/edk2-samurai-out/kernel154')

def extract(s,name):
    m=re.search(r'^(?:static )?(?:int|void) '+name+r'\([^;]+?\n\{',s,re.M)
    assert m,name
    end=m.end();depth=1
    while depth:
        if s[end]=='{':depth+=1
        elif s[end]=='}':depth-=1
        end+=1
    return s[m.start():end]+'\n'

results=[]
for label,path in [('baseline153',out/'dsi-before153-private.c'),('candidate154',k/'drivers/gpu/drm/msm/dsi/dsi_host.c')]:
    d=out/('tests-'+label);d.mkdir(exist_ok=True)
    source=path.read_text()
    names=['dsi_sw_reset']
    if label=='candidate154':names=['dsi_ctrl_disable']+names+['dsi_log_power_on_state']
    names+=['msm_dsi_host_power_on']
    (d/'actual-host-functions.h').write_text('\n'.join(extract(source,n) for n in names))
    for sanitized in [False,True]:
        exe=d/('sanitized' if sanitized else 'plain')
        cmd=['cc','-std=gnu11','-Wall','-Wextra','-Werror','-g','-I'+str(d),str(ref/'test-host-init.c'),'-o',str(exe)]
        if sanitized:cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
        subprocess.run(cmd,check=True)
        r=subprocess.run([str(exe)],capture_output=True,text=True,timeout=10)
        (d/(exe.name+'.log')).write_text(r.stdout+r.stderr)
        failures=[x.split()[1] for x in r.stdout.splitlines() if x.endswith('FAIL')]
        results.append(dict(label=label,sanitized=sanitized,exit=r.returncode,
            cases=r.stdout.count('CASE '),failures=failures,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        assert not r.stderr,r.stderr
        if label=='candidate154':assert r.returncode==0 and not failures,r.stdout
        else:assert r.returncode==1 and len(failures)==3,r.stdout
report=dict(stage=154,actual_function_extraction=True,results=results,
    hardware_clocks_and_timing_are_stubs=True,hardware_root_cause_confirmed=False)
(ref/'actual-function-test-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
