from pathlib import Path
import hashlib,json,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
def read(name):
    path=out/(name+'.tar')
    with tarfile.open(path) as archive:
        data={}
        for entry in archive:
            assert not entry.issym() and not entry.islnk()
            if not entry.isfile():continue
            key=entry.name.removeprefix('./')
            assert not Path(key).is_absolute() and '..' not in Path(key).parts and key not in data
            data[key]=archive.extractfile(entry).read()
    count=0
    for line in data['SHA256SUMS'].decode().splitlines():
        digest,key=line.split('  ',1)
        assert hashlib.sha256(data[key.removeprefix('./')]).hexdigest()==digest
        count+=1
    return data,hashlib.sha256(path.read_bytes()).hexdigest(),count
data,digest,count=read('display-linear15-failed')
assert data['trial-exit.txt'].strip()==b'1'
assert b'ORIGINAL_LAUNCHER_RESTORED_AFTER_INCOMPLETE_TRIAL' in data['rollback.txt']
assert data['launcher-restored.txt'].strip()==b'ORIGINAL_LAUNCHER_MATCH'
original=data['launcher-before-private.sh'];candidate=data['launcher-trial-private.sh']
assert candidate==original.replace(b'#!/bin/sh\n',b'#!/bin/sh\nexport WLR_DRM_NO_MODIFIERS=1\n',1)
assert 'phoc-no-modifiers.txt' not in data and 'drm-0.txt' not in data
assert data['tracing-on.txt'].strip()==b'0'
assert b'modifier=0x500000000000001' in data['drm-after-rollback.txt']
assert data['phoc-after-rollback.txt'].strip() and data['phosh-after-rollback.txt'].strip()
assert data['slpi-after.txt'].strip()==b'offline' and data['power-after.txt'].strip()==b'vdd=0 vddio=0'
assert data['nv-check.txt'].count(b': OK')==6 and data['source-check.txt'].count(b': OK')==4
assert b': OK' in data['greetd-unchanged.txt']
before=data['dmesg-before.txt'];after=data['dmesg-after-rollback.txt']
report=dict(archive_sha256=digest,nested_files_verified=count,boot_checkpoint='reboot-audio-clean-15',
    trial_exit=1,no_modifiers_environment_confirmed=False,linear_buffer_verified=False,
    original_launcher_restored_byte_for_byte=True,launcher_candidate_only_change='WLR_DRM_NO_MODIFIERS=1',
    phosh_restored=True,current_modifier='0x500000000000001',
    taint_before=int(data['state-before.txt'].splitlines()[-1]),taint_after=int(data['state-after-rollback.txt'].splitlines()[-1]),
    new_dpu_timeouts=after.count(b'frame done timeout')-before.count(b'frame done timeout'),
    total_dpu_timeouts=after.count(b'frame done timeout'),gpu_faults=after.count(b'*** gpu fault'),
    new_kernel_warnings=after.count(b'WARNING:')-before.count(b'WARNING:'),
    slpi_offline_sensor_power_off=True,nv6_sources4_unchanged=True,
    permanent_display_fix_accepted=False,goal_complete=False)
(ref/'display-linear15-failed-validation.json').write_text(json.dumps(report,indent=2)+'\n')
idle,digest,count=read('display-idle-restored15')
result=json.loads(idle['result.json'])
assert result['before']=='uint32 0' and result['after']=='uint32 60' and result['original_idle_policy_restored']
assert idle['boot-id-private.txt']==data['boot-id-private.txt']
result.update(archive_sha256=digest,nested_files_verified=count,taint=int(idle['taint.txt']),goal_complete=False)
(ref/'display-idle-restored15-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(failed_trial=report,idle_restoration=result),indent=2))
