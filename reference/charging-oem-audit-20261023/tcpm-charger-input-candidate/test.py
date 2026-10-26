"""Exercise actual budget/collection/notifier functions; no phone or live IO."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
BASE=REF/'charging-session-20261023/charge-timer-hold-r2-candidate'
OUT=Path('/home/cy122/charging-management-20261023/tcpm-charger-input-tests-01')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def function(source,name):
    m=re.search(r'^static [^\n]*\b'+name+r'\(',source,re.M)
    assert m,name
    start=m.start();end=source.index('\n}\n',start)+3
    return source[start:end]

def main():
    assert not OUT.exists(),'Inspect prior result; do not overwrite evidence'
    baseline=(BASE/'samurai-mp2650.c').read_text()
    source=(HERE/'samurai-mp2650.c').read_text()
    assert sha(BASE/'samurai-mp2650.c')=='32fa5840d28fd5cbe7366e8d0951e9cd20b87dff6263d49d3386cd3a3e486ed6'
    unchanged=['sm_step_locked','sm_gauge_sample','sm_named_supply','sm_stop_locked',
               'sm_work','sm_get_property','sm_set_property']
    # Names are verified below against the installed source; no policy-body rewrite.
    common=[]
    for name in re.findall(r'^static [^\n]*\b(sm_\w+)\(',baseline,re.M):
        if name in ('sm_collect','sm_supply_changed','sm_probe'):continue
        assert function(baseline,name)==function(source,name),name
        common.append(name)
    for name in unchanged:
        if name in common:assert function(baseline,name)==function(source,name)
    names=['sm_psy_int','sm_read_typec_allowance','sm_input_budget','sm_collect','sm_supply_changed']
    OUT.mkdir(mode=0o700)
    (OUT/'actual-input-functions.inc').write_text('\n'.join(function(source,n) for n in names))
    header=Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01/source354/include/linux/power_supply.h')
    enum=re.search(r'enum power_supply_usb_type\s*\{.*?\};',header.read_text(),re.S)
    assert enum
    (OUT/'kernel-usb-types.inc').write_text(enum.group())
    argv=['cc','-std=c11','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
          '-fno-omit-frame-pointer','-I'+str(OUT),'-I'+str(HERE),str(HERE/'test-input.c'),'-o',str(OUT/'test-input')]
    build=subprocess.run(argv,capture_output=True,text=True)
    (OUT/'build.stderr').write_text(build.stderr)
    assert build.returncode==0,build.stderr
    run=subprocess.run([str(OUT/'test-input')],capture_output=True,text=True)
    (OUT/'run.stdout').write_text(run.stdout);(OUT/'run.stderr').write_text(run.stderr)
    assert run.returncode==0,run.stdout+run.stderr
    result=dict(passed=True,command=argv,returncode=run.returncode,result=json.loads(run.stdout),
        actual_functions=names,unchanged_existing_functions=common,
        source_sha256=sha(HERE/'samurai-mp2650.c'),header_sha256=sha(HERE/'negotiated-input.h'),
        kernel_header_sha256=sha(header),test_sha256=sha(HERE/'test-input.c'),
        phone_accessed=False,installed=False,PD_APSD_coexistence_accepted=False,
        snapshot_scope='Repeated software snapshots; not an electrical atomicity guarantee')
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    with (HERE/'test-result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))

if __name__=='__main__':main()
