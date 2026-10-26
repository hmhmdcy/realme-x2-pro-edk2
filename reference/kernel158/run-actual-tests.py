from pathlib import Path
import hashlib,json,re,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel158');out=Path('/mnt/e/edk2-samurai-out/kernel158')
before=json.loads((out/'source-before-private.json').read_text())
spec=[('drivers/gpu/drm/msm/dsi/dsi_host.c','msm_dsi_host_quiesce_firmware'),('drivers/gpu/drm/msm/dsi/dsi_manager.c','dsi_mgr_bridge_power_on'),
    ('drivers/gpu/drm/msm/dsi/dsi.c','msm_dsi_quiesce_firmware'),('drivers/gpu/drm/msm/disp/dpu1/dpu_kms.c','dpu_kms_quiesce_boot_dsi')]
def extract(s,name):
    m=re.search(r'^(?:static )?int '+name+r'\([^;]+?\n\{',s,re.M);assert m,name
    end=m.end();depth=1
    while depth:
        if s[end]=='{':depth+=1
        elif s[end]=='}':depth-=1
        end+=1
    return s[m.start():end]+'\n'
body=extract((k/spec[-1][0]).read_text(),'dpu_kms_hw_init')
assert body.index('dpu_kms_quiesce_boot_dsi(kms)')<body.index('dpu_rm_clear_boot_config(')
assert body.index('qcom,sm8150-dpu')<body.index('dpu_kms_quiesce_boot_dsi(kms)')
results=[]
for label in ['baseline157','candidate158']:
    d=out/('tests-'+label);d.mkdir(exist_ok=True);funcs=[];hashes={}
    for n,name in spec:
        s=before[n] if label=='baseline157' and n in before else (k/n).read_text();hashes[n]=hashlib.sha256(s.encode()).hexdigest()
        if label=='baseline157' and name in ['msm_dsi_quiesce_firmware','dpu_kms_quiesce_boot_dsi']:continue
        funcs.append(extract(s,name))
    (d/'actual-functions.h').write_text('\n'.join(funcs))
    for sanitized in [False,True]:
        exe=d/('sanitized' if sanitized else 'plain')
        args=['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function','-g','-I'+str(d),str(ref/'test-before-ctl.c'),'-o',str(exe)]
        if label=='baseline157':args+=['-DBASELINE']
        if sanitized:args+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
        subprocess.run(args,check=True);r=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
        (d/(exe.name+'.log')).write_text(r.stdout+r.stderr)
        failures=[s.split()[1] for s in r.stdout.splitlines() if s.endswith('FAIL')]
        result=dict(label=label,sanitized=sanitized,exit=r.returncode,cases=r.stdout.count('CASE '),failures=failures,source_sha256=hashes);results.append(result)
        assert not r.stderr,r.stderr
        assert r.returncode==(1 if label=='baseline157' else 0),r.stdout
        assert len(failures)==(2 if label=='baseline157' else 0),r.stdout
        assert result['cases']==(4 if label=='baseline157' else 22),r.stdout
report=dict(stage=158,actual_function_extraction=True,results=results,
    source_integration_before_ctl_clear_confirmed=True,sm8150_cleanup_scope_confirmed=True,
    hardware_clocks_and_mmio_are_stubs=True,real_boot_validation_pending=True)
(ref/'actual-function-test-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
