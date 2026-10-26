from pathlib import Path
import hashlib,json,tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel154')
out=Path('/mnt/e/edk2-samurai-out/kernel154')
archive=out/'evidence-private.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='be13033bb98467faa858cdd4840d2b2554d54baa6cfddaeac5a73b7cd93be395'
with tarfile.open(archive) as tar:
    for label,filename in [('k154-first-startup','first-startup-validation.json'),
        ('k154-wake-recovery','wake-recovery-validation.json'),('k154-first-runtime','first-runtime-validation.json')]:
        result=json.load(tar.extractfile(label+'/result.json'))
        result.update(stage=154,hardware_bug_fixed=False)
        if label.endswith('startup'):result.update(user_initial_report='White screen with garbling and flicker in part of the screen')
        if label.endswith('runtime'):result.update(full_boot_zero_display_error_gate_pass=False,expected_process_exit=1)
        if label.endswith('recovery'):result.update(user_optical_recovery_confirmed=True,user_report='Desktop or lockscreen restored')
        (ref/filename).write_text(json.dumps(result,indent=2)+'\n')
report=dict(stage=154,archive_bytes=archive.stat().st_size,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    private_raw_data_preserved=True,first_register_snapshot_inactive=True,register_fault_vs_normal_comparison_rejected=True)
(ref/'evidence-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K154_FAILURE_AND_RECOVERY_FACTS_SAVED')
