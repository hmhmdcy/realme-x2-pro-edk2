from pathlib import Path
import hashlib,json,re,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel156')
out=Path('/mnt/e/edk2-samurai-out/kernel156')
before=json.loads((out/'source-before-private.json').read_text())
spec=[('drivers/gpu/drm/drm_panel.c',['drm_panel_init','drm_panel_enable_backlight','drm_panel_first_frame_done','drm_panel_enable','drm_panel_disable']),
    ('drivers/gpu/drm/bridge/panel.c',['drm_panel_bridge_needs_first_frame','drm_panel_bridge_first_frame_done']),
    ('drivers/gpu/drm/msm/disp/dpu1/dpu_kms.c',['dpu_kms_first_frame_backlight']),
    ('drivers/gpu/drm/panel/panel-samsung-sofef03f.c',['sofef03f_bl_update'])]
def extract(s,name):
    m=re.search(r'^(?:static )?(?:int|void|bool) '+name+r'\([^;]+?\n\{',s,re.M)
    assert m,name
    end=m.end();depth=1
    while depth:
        if s[end]=='{':depth+=1
        elif s[end]=='}':depth-=1
        end+=1
    return s[m.start():end]+'\n'
results=[]
for label in ['baseline154','candidate156']:
    d=out/('tests-'+label);d.mkdir(exist_ok=True)
    funcs=[];hashes={}
    for path,names in spec:
        s=before[path] if label=='baseline154' else (k/path).read_text()
        hashes[path]=hashlib.sha256(s.encode()).hexdigest()
        if label=='baseline154':names=[n for n in names if n in ['drm_panel_init','drm_panel_enable','drm_panel_disable','sofef03f_bl_update']]
        funcs += [extract(s,n) for n in names]
    (d/'actual-first-frame-functions.h').write_text('\n'.join(funcs))
    for sanitized in [False,True]:
        exe=d/('sanitized' if sanitized else 'plain')
        cmd=['cc','-std=gnu11','-Wall','-Wextra','-Werror','-pthread','-g','-I'+str(d),str(ref/'test-first-frame.c'),'-o',str(exe)]
        if sanitized:cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
        if label=='baseline154':cmd+=['-DBASELINE']
        subprocess.run(cmd,check=True)
        r=subprocess.run([str(exe)],capture_output=True,text=True,timeout=15)
        (d/(exe.name+'.log')).write_text(r.stdout+r.stderr)
        failed=[x.split()[1] for x in r.stdout.splitlines() if x.endswith('FAIL')]
        result=dict(label=label,sanitized=sanitized,exit=r.returncode,cases=r.stdout.count('CASE '),failures=failed,source_sha256=hashes)
        results.append(result)
        assert not r.stderr,r.stderr
        if label=='candidate156':assert r.returncode==0 and not failed,r.stdout
        else:assert r.returncode==1 and len(failed)==2,r.stdout
report=dict(stage=156,actual_function_extraction=True,results=results,
    hardware_and_irq_are_stubs=True,hardware_pixel_validity_not_proven=True)
(ref/'actual-function-test-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
