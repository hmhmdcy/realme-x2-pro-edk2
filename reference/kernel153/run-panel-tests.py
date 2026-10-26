from pathlib import Path
import hashlib,json,re,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel153')
out=Path('/mnt/e/edk2-samurai-out/kernel153')
def extract(s,name):
    m=re.search(r'^static (?:int|void) '+name+r'\([^;]+?\n\{',s,re.M)
    assert m,name
    end=m.end();depth=1
    while depth:
        if s[end]=='{':depth+=1
        elif s[end]=='}':depth-=1
        end+=1
    return s[m.start():end]+'\n'
results=[]
for label,path in [('baseline147',out/'panel-before147-private.c'),('candidate153',k/'drivers/gpu/drm/panel/panel-samsung-sofef03f.c')]:
    d=out/('tests-'+label);d.mkdir(exist_ok=True)
    s=path.read_text()
    begin=s.index('\tctx->reset = devm_gpiod_get');end=s.index('\tctx->panel.backlight =',begin)
    gpio_only='static int actual_probe_gpios(struct sofef03f *ctx)\n{\n\tstruct device *dev = &ctx->dsi->dev;\n'+s[begin:end]+'\treturn 0;\n}\n'
    names=['sofef03f_supply_enable','sofef03f_supply_disable','sofef03f_power_off']
    if label=='candidate153':names+=['sofef03f_init_gpios']
    names+=['sofef03f_prepare']
    (d/'actual-panel-functions.h').write_text(gpio_only+'\n'.join(extract(s,n) for n in names))
    for san in [False,True]:
        exe=d/('sanitized' if san else 'plain')
        cmd=['cc','-std=gnu11','-Wall','-Wextra','-Werror','-g','-I'+str(d),str(ref/'test-panel-handoff.c'),'-o',str(exe)]
        if san:cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
        subprocess.run(cmd,check=True)
        p=subprocess.run([str(exe)],capture_output=True,text=True,timeout=10)
        (d/(exe.name+'.log')).write_text(p.stdout+p.stderr)
        results.append(dict(label=label,sanitizer=san,exit=p.returncode,output=p.stdout,
            source_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        if label=='candidate153':assert p.returncode==0 and not p.stderr,p.stdout+p.stderr
        else:
            assert p.returncode==1 and p.stdout.count(' FAIL')==5 and not p.stderr,p.stdout+p.stderr
report=dict(stage=153,actual_function_extraction=True,probe_gpio_fragment_from_actual_source=True,
    results=results,hardware_and_attachments_are_stubs=True,hardware_first_boot_verified=False)
(ref/'actual-function-test-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
