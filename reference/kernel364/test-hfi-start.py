from pathlib import Path
import json,shutil,subprocess
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel364');backing=P/'start-regression';backing.mkdir(exist_ok=True)
shutil.copyfile(HERE/'hfi-start-regression.c',backing/'probe.c');results=[]
for label,path in [('old',HERE.parent/'kernel356/kernel/camss-icp-a5-boot.c'),('new',P/'boot-proposed.c')]:
    text=path.read_text();a=text.index('int camss_a5_start(');b=text.index('EXPORT_SYMBOL_GPL(camss_a5_start)',a)
    (backing/'start-method.inc').write_text(text[a:b])
    q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=address,undefined',str(backing/'probe.c'),'-o',str(backing/'probe')],capture_output=True)
    assert not q.returncode,q.stderr.decode()
    for case in (range(8) if label=='new' else [0,1,2,3]):
        q=subprocess.run([str(backing/'probe'),str(case)],capture_output=True,timeout=10);(P/f'start-{label}-{case}.log').write_bytes(q.stdout+q.stderr)
        expected=label=='new' or case in [0,3];assert (q.returncode==0)==expected,(label,case,q.stderr.decode()[-2000:])
        results.append(dict(source=label,case=case,expected_pass=expected,exit_code=q.returncode,matched=True))
report=dict(stage=364,verbatim_start_function=True,platform_and_poll_providers_mocked=True,asan_ubsan=True,
    waits_through_three_until_one=True,persistent_three_times_out=True,no_sys_init_before_exact_ready=True,timeout_and_error_cleanup_verified=True,tests=results,passed=True)
(HERE/'start-regression-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
