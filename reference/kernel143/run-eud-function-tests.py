from pathlib import Path
import hashlib
import json
import re
import subprocess

root=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel143')
out=Path('/mnt/e/edk2-samurai-out/kernel143')
source=root.joinpath('drivers/tty/serial/eud.c').read_text()
meta=json.loads(ref.joinpath('source-preparation-validation.json').read_text())
assert hashlib.sha256(source.encode()).hexdigest()==meta['candidate_source_sha256']
names=['to_eud_port','eud_put','eud_send_frame','eud_tx_work','eud_shutdown','eud_console_write_legacy',
    'eud_console_device_lock','eud_console_device_unlock','eud_console_write_thread','eud_console_write_atomic']
parts=[]
for name in names:
    match=re.search(r'^static[^;{}]*\b'+name+r'\([^;{}]*\)\n\{',source,re.M)
    assert match,name
    depth=1;end=match.end()
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    parts.append(source[match.start():end])
assert 'CON_PRINTBUFFER | CON_NBCON | CON_NBCON_ATOMIC_UNSAFE' in source
assert not re.search(r'^\s*\.cons\s*=',source,re.M) and 'uart_port_set_cons' not in source
assert root.joinpath('kernel/printk/internal.h').read_text().find('#define PRINTK_MESSAGE_MAX\t2048')>=0
testdir=out/'host-tests-private'
testdir.mkdir(mode=0o700,exist_ok=True)
assert not ref.joinpath('actual-function-test-validation.json').exists(), 'Finished tests must not be replayed without a new change or concern'
testdir.joinpath('eud-generated-functions.h').write_text('\n\n'.join(parts)+'\n')
base=['gcc','-std=c11','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-pthread','-I',str(testdir),str(ref/'test-eud-functions.c')]
results={}
for name,flags in [('plain',[]),('asan-ubsan',['-fsanitize=address,undefined','-fno-omit-frame-pointer'])]:
    executable=testdir/('test-'+name)
    compile_result=subprocess.run(base+flags+['-o',str(executable)],capture_output=True,text=True)
    testdir.joinpath(name+'-compile-private.txt').write_text(compile_result.stdout+compile_result.stderr)
    assert compile_result.returncode==0,compile_result.stderr
    run=subprocess.run([str(executable)],capture_output=True,text=True,timeout=30)
    testdir.joinpath(name+'-run-private.txt').write_text(run.stdout+run.stderr)
    assert run.returncode==0,run.stdout+run.stderr
    assert 'cases passed: 16;' in run.stdout and not run.stderr
    results[name]=dict(returncode=run.returncode,cases=16,compiler_diagnostics_empty=True,sanitizer_diagnostics_empty=not run.stderr)
report=dict(stage=143,baseline_kernel_build=140,candidate_source_sha256=meta['candidate_source_sha256'],
    actual_driver_functions_extracted=names,actual_function_cases=16,results=results,
    modeled_85_byte_total_tx_pacing_us=69800,modeled_normal_max_port_irq_off_us=3200,
    modeled_legacy_whole_record_irq_off_us=69800,whole_console_and_tty_records_serialized=True,
    ownership_loss_before_and_between_frames_checked=True,rx_error_and_f1_work_scheduling_checked=True,
    tty_close_drain_and_empty_or_stopped_states_checked=True,
    limits='Host stubs model locks, MMIO pacing and ownership loss; not a running-kernel timing or panic acceptance test.',
    actual_functions_tested=True,kernel_build_completed=False,deployed=False,goal_complete=False)
ref.joinpath('actual-function-test-validation.json').write_text(json.dumps(report,indent=2)+'\n')
meta['actual_functions_tested']=True
ref.joinpath('source-preparation-validation.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(report,indent=2))
