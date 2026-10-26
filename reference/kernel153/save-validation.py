from pathlib import Path
import hashlib,json,tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel153')
out=Path('/mnt/e/edk2-samurai-out/kernel153')
assert hashlib.sha256((out/'wake-results-private.tar.gz').read_bytes()).hexdigest()=='b1ab0cdf317eb5e1a72a569ae1ae0b956e7a72b1863f4e26e90196f70519cf5e'
with tarfile.open(out/'first-startup-private.tar.gz') as tar:
    result=json.load(tar.extractfile('k153-first-startup/result.json'))
    result.update(stage=153,hardware_bug_fixed=False,logdump_deployed=True,
        firmware_ctl0_clear_succeeded=True,automatic_desktop=True,panel_rebind_required=False,
        user_report='Lockscreen visible; transient garbling and flicker on power-key wake',
        optical_wake_fix_verified=False)
    (ref/'first-startup-validation.json').write_text(json.dumps(result,indent=2)+'\n')
with tarfile.open(out/'wake-results-private.tar.gz') as tar:
    for label,filename in [('k153-wake-recovery','wake-recovery-validation.json'),
        ('k153-settled-cycles','settled-cycles-validation.json'),
        ('k153-first-runtime-retry1','first-runtime-validation.json')]:
        r=json.load(tar.extractfile(label+'/result.json'))
        if label.endswith('retry1'):r.update(full_boot_zero_display_error_gate_pass=False,
            expected_process_exit=1,initial_missing_dependency_attempt_preserved=True)
        (ref/filename).write_text(json.dumps(r,indent=2)+'\n')
print('K153_PUBLIC_FACTS_SAVED')
