from pathlib import Path
import hashlib,json,re,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel157')
out=Path('/mnt/e/edk2-samurai-out/kernel157')
before=json.loads((out/'source-before-private.json').read_text())
spec=[('drivers/gpu/drm/msm/dsi/dsi_host.c','msm_dsi_host_quiesce_firmware'),('drivers/gpu/drm/msm/dsi/dsi_manager.c','dsi_mgr_bridge_power_on')]
def extract(s,name):
    m=re.search(r'^(?:static )?int '+name+r'\([^;]+?\n\{',s,re.M);assert m,name
    end=m.end();depth=1
    while depth:
        if s[end]=='{':depth+=1
        elif s[end]=='}':depth-=1
        end+=1
    return s[m.start():end]+'\n'
results=[]
for label in ['baseline156','candidate157']:
    d=out/('tests-'+label);d.mkdir(exist_ok=True);funcs=[];hashes={}
    for n,name in spec:
        s=before[n] if label=='baseline156' else (k/n).read_text();hashes[n]=hashlib.sha256(s.encode()).hexdigest()
        if label=='baseline156' and name=='msm_dsi_host_quiesce_firmware':continue
        funcs.append(extract(s,name))
    (d/'actual-functions.h').write_text('\n'.join(funcs))
    for sanitized in [False,True]:
        exe=d/('sanitized' if sanitized else 'plain')
        args=['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function','-g','-I'+str(d),str(ref/'test-early-host-stop.c'),'-o',str(exe)]
        if label=='baseline156':args+=['-DBASELINE']
        if sanitized:args+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
        subprocess.run(args,check=True)
        r=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
        (d/(exe.name+'.log')).write_text(r.stdout+r.stderr)
        failures=[s.split()[1] for s in r.stdout.splitlines() if s.endswith('FAIL')]
        result=dict(label=label,sanitized=sanitized,exit=r.returncode,cases=r.stdout.count('CASE '),failures=failures,source_sha256=hashes)
        results.append(result)
        assert not r.stderr,r.stderr
        assert r.returncode==(1 if label=='baseline156' else 0),r.stdout
        assert len(failures)==(2 if label=='baseline156' else 0),r.stdout
report=dict(stage=157,actual_function_extraction=True,results=results,hardware_clocks_and_mmio_are_stubs=True,real_boot_validation_pending=True)
(ref/'actual-function-test-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
