"""New owner functions + real DWC stop/core-exit/prepare; no old suites."""
from pathlib import Path
import hashlib, json, re, subprocess
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def clean(t): return '\n'.join(x for x in t.splitlines() if not x.startswith('#include'))+'\n'
def function(text,name):
    match=re.search(r'(?m)^(?:static )?(?:int|void) '+name+r'\([^;]*?\)\n\{',text)
    assert match,name
    start=match.start(); end=match.end(); level=1
    while level:
        level+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]+'\n'
coreh=(HERE/'core.h').read_text()
windows=coreh[coreh.index('enum dwc3_gadget_window_state {'):coreh.index('/**\n * struct dwc3 -')]
headers='\n'.join(clean(p.read_text()) for p in [HERE/'samurai-apsd-backend.h',HERE/'samurai-apsd-owner.h',
    REF/'charging-oem-audit-20261023/apsd-once-candidate/samurai-apsd-once.h',
    REF/'charging-session-20261023/eud-runtime-window-candidate-r2/eud-com-window.h',
    REF/'charging-oem-audit-20261023/apsd-phy-window-candidate/phy-qcom-snps-femto-v2-window.h'])
body=clean((HERE/'samurai-apsd-owner.c').read_text())
actual='\n'.join([function((HERE/'gadget.c').read_text(),'dwc3_gadget_stop'),
                   function((HERE/'core.c').read_text(),'dwc3_core_exit'),
                   function((HERE/'core.c').read_text(),'dwc3_pm_prepare')])
test=(HERE/'test-fixture.c').read_text()
fixture=test.replace('/* ACTUAL_HEADERS */',headers).replace('/* ACTUAL_WINDOWS */',windows).replace('/* ACTUAL_OWNER */',body).replace('/* ACTUAL_LIFECYCLE */',actual)
out=HERE/'test-private';out.mkdir(exist_ok=True)
(out/'actual-owner.c').write_text(fixture)
cmd=['gcc','-std=gnu11','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(out/'actual-owner.c'),'-o',str(out/'test-owner')]
q=subprocess.run(cmd,capture_output=True,text=True)
(out/'compile.txt').write_text(q.stdout+q.stderr)
if q.returncode: print(q.stderr);raise SystemExit(q.returncode)
q=subprocess.run([str(out/'test-owner')],capture_output=True,text=True)
(out/'run.txt').write_text(q.stdout+q.stderr)
print(q.stdout+q.stderr)
result={'passed':q.returncode==0,'exit_code':q.returncode,'scope':'new actual owner functions and extracted actual DWC UDC stop/core_exit/pm_prepare; fake OS/component/bus boundaries; no real gate/hardware proof',
        'cases':q.stdout.splitlines(),'files':{n:sha(HERE/n) for n in ['samurai-apsd-owner.c','samurai-apsd-owner.h','samurai-apsd-backend.h','core.c','core.h','gadget.c','test-owner.py','test-fixture.c']},
        'actual_fixture_sha256':sha(out/'actual-owner.c'),'compile_command':cmd,'old_suites_rerun':False,'device_accessed':False}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
raise SystemExit(q.returncode)
