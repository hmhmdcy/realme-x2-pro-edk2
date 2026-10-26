from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile

out=Path('/mnt/e/edk2-samurai-out/kernel99')
files={}
with tarfile.open(out/'haptics-initial-retry1.tar') as archive:
    for member in archive:
        if not member.isfile(): continue
        parts=PurePosixPath(member.name).parts
        assert parts[0]=='k99-haptics-initial-retry1' and '..' not in parts
        name=str(PurePosixPath(*parts[1:]));assert name not in files
        files[name]=archive.extractfile(member).read()
checked=set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);name=name.removeprefix('./')
    assert name not in checked and hashlib.sha256(files[name]).hexdigest()==digest
    checked.add(name)
assert checked==files.keys()-{'SHA256SUMS'}
assert files['result.txt']==b'HAPTICS_FF_AND_ELECTRICAL_PASS\n'
assert files['of-node.txt'].decode().strip().endswith('/geniqup@8c0000/i2c@89c000/haptics@5a')
for n in range(1,4):
    assert files[f'pulse{n}.log']==b'FF_UPLOAD_PASS\nFF_START_PASS\nFF_STOP_PASS\nFF_ERASE_PASS\n'
    samples=files[f'pulse{n}-samples.txt'].decode()
    assert 'go=01 state=06 ' in samples and 'active=1' in samples
    after=files[f'status-after{n}.txt'].decode()
    assert re.search(r'^id=97 go=00 state=00 .*active=0 ',after)
    assert f'starts={n} stops={n} watchdog_stops=0 error=0\n' in after
state=files['state.txt'].decode().splitlines()
assert '#98 SMP PREEMPT' in state[0] and state[3]=='0'
before=files['dmesg-before.txt'].decode();after=files['dmesg-after.txt'].decode()
assert 'AW8697 id=97 standby' in before
assert 'haptics stopped; reset held after error' not in after
assert before.count('frame done timeout')==after.count('frame done timeout')
report=dict(haptics_ff_and_electrical_audit_pass=True,kernel_build=98,logical_stage=99,
    verified_private_files=len(checked),archive_sha256=hashlib.sha256((out/'haptics-initial-retry1.tar').read_bytes()).hexdigest(),
    chip_id='0x97',controller='89c000',standard_ff_rumble=True,
    pulse_count=3,strength_percent=20,requested_duration_ms=150,
    go_and_continuous_state_observed_each_pulse=True,standby_restored_each_pulse=True,
    fault_count=0,taint=0,new_display_timeout_during_test=False,
    physical_vibration_confirmed=False,cold_power_boot_tested=False,suspend_resume_tested=False,
    radio_auto_boot_failed_before_mpss_start=True,radio_issue_fixed_in_flash=False,goal_complete=False)
(out/'haptics-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
