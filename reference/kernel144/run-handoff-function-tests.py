from pathlib import Path
import hashlib
import json
import re
import subprocess
root=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel144');out=Path('/mnt/e/edk2-samurai-out/kernel144')
meta=json.loads(ref.joinpath('source-preparation-validation.json').read_text())
candidate=root.joinpath('drivers/tty/serial/eud.c').read_text()
assert hashlib.sha256(candidate.encode()).hexdigest()==meta['candidate_source_sha256']
assert not ref.joinpath('actual-function-test-validation.json').exists()
names=['to_eud_port','eud_put','eud_send_frame','eud_tx_work','eud_shutdown','eud_console_write_legacy',
    'eud_console_device_lock','eud_console_device_unlock','eud_console_write_thread','eud_console_write_atomic','eud_restore_ahb2phy','eud_reboot_cmd']
results={}
for label,source,defines,expected in [('baseline143',out.joinpath('eud-before-private.c').read_text(),['-DBASELINE143'],18),('candidate144',candidate,[],26)]:
    directory=out/'host-tests-private'/label;directory.mkdir(mode=0o700,parents=True)
    parts=[]
    for name in names:
        match=re.search(r'^static[^;{}]*\b'+name+r'\([^;{}]*\)\n\{',source,re.M);assert match,name
        end=match.end();depth=1
        while depth:depth+=(source[end]=='{')-(source[end]=='}');end+=1
        parts.append(source[match.start():end])
    directory.joinpath('eud-generated-functions.h').write_text('\n\n'.join(parts)+'\n')
    for mode,flags in [('plain',[]),('asan-ubsan',['-fsanitize=address,undefined','-fno-omit-frame-pointer'])]:
        exe=directory/('test-'+mode)
        compile_run=subprocess.run(['gcc','-std=c11','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-pthread',*defines,*flags,'-I',str(directory),str(ref/'test-eud-handoff.c'),'-o',str(exe)],capture_output=True,text=True)
        directory.joinpath(mode+'-compile-private.txt').write_text(compile_run.stdout+compile_run.stderr)
        assert compile_run.returncode==0,compile_run.stderr
        run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30)
        directory.joinpath(mode+'-run-private.txt').write_text(run.stdout+run.stderr)
        assert run.returncode==0,run.stdout+run.stderr
        assert not run.stderr
        assert ('cases: 18' if label=='baseline143' else 'cases passed: 26') in run.stdout
        results[label+'-'+mode]=dict(returncode=0,cases=expected,compiler_diagnostics_empty=True,sanitizer_diagnostics_empty=True)
report=dict(stage=144,actual_driver_functions_extracted=names,candidate_source_sha256=meta['candidate_source_sha256'],
    candidate_cases=26,baseline143_regressions_reproduced=['queued F1 not sent before disable','TTY MMIO after hardware disable'],
    results=results,previous16_normal_cases_preserved=True,
    queued_notice_flush_and_printer_retirement_checked=True,hardware_handoff_excludes_late_normal_and_atomic_tx=True,
    rx_irq_synchronization_duplicate_and_bad_length_checked=True,
    failed_first_flush_followed_by_unregister_flush_checked=True,active_printer_and_reboot_concurrency_checked=True,
    limits='Host models printk queue and core flush/retirement; real host F1 receipt, panic and DSI acceptance remain required.',
    actual_functions_tested=True,deployed=False,goal_complete=False)
ref.joinpath('actual-function-test-validation.json').write_text(json.dumps(report,indent=2)+'\n')
meta['actual_functions_tested']=True;ref.joinpath('source-preparation-validation.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(report,indent=2))
