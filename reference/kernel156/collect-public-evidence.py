from pathlib import Path
import hashlib,json,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel156');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel156')
for name in ['startup-validation.json','cycles-validation.json','runtime-validation.json','first-frame-order-validation.json',
    'matched-active-register-comparison.json','boot-order-validation.json']:
    (ref/name).write_bytes((out/name).read_bytes())
with tarfile.open(out/'first-validation-private.tar.gz') as t:
    timing=json.loads(t.extractfile('k156-boot-timing/result.json').read())
processes=timing['process_start_uptime']
report=dict(stage=156,process_start_uptime=processes,process_timestamps_from_monotonic_proc_stat=True,
    phosh_start_uptime=min(processes['phosh']),previous155_phosh_start_uptime=79.67,
    phosh_start_improvement_seconds=79.67-min(processes['phosh']),
    phosh_before_networkmanager=min(processes['phosh'])<min(processes['NetworkManager']),
    original_service_wallclock_timestamps_invalid=True,
    service_wallclock_reason='Clock changed after service links were created; negative boot uptimes rejected.',
    physical_lockscreen_timing_validation_pending=True)
(ref/'boot-timing-validation.json').write_text(json.dumps(report,indent=2)+'\n')
proofs={}
for name in ['full-startup-private.tar.gz','startup-small-private.tar.gz','first-validation-private.tar.gz','preflash-private.tar.gz','quiesce-private.tar']:
    p=out/name;proofs[name]=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(ref/'evidence-archives.json').write_text(json.dumps(proofs,indent=2)+'\n')
summary=dict(stage=156,actual_kernel_build=156,logdump_readback_exact=True,boot_persist_nv_and_modules_preserved=True,
    first_frame_backlight_real_hardware_order_pass=True,standard_dpms_transitions=24,new_errors_in_dpms=0,
    initial_boot_dsi_errors=78,full_boot_zero_dsi_acceptance=False,
    hardware_physical_verification_pending=True,user_temporarily_away=True,
    temporary_startup_recorder_stopped_and_removed_from_boot=True,goal_complete=False)
(ref/'deployment-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(dict(timing=report,archive_proofs=proofs,deployment=summary)),flush=True)
