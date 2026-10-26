from pathlib import Path
import hashlib,json,re,struct,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel113');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
reports={}
for label,archive in [('no_fbcon','display-no-fbcon-boot15.tar'),('wake','display-wake15.tar')]:
    path=out/archive
    with tarfile.open(path) as tar:
        data={}
        for item in tar:
            assert not item.issym() and not item.islnk()
            if not item.isfile():continue
            key=item.name.removeprefix('./');assert not Path(key).is_absolute() and '..' not in Path(key).parts and key not in data
            data[key]=tar.extractfile(item).read()
    for line in data['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1);assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
    with tarfile.open(out/'reboot-audio-clean-15.tar') as tar:
        assert data['boot-id-private.txt']==tar.extractfile('./boot-id-private.txt').read()
    before=data['dmesg-before.txt'];after=data['dmesg-after.txt'];assert after.startswith(before)
    new=after[len(before):]
    assert data['slpi-after.txt'].strip()==b'offline' and data['power-after.txt'].strip()==b'vdd=0 vddio=0'
    assert data['fbcon-after.txt'].strip()==b'0'
    report=dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        taint_before=int(data['state-before.txt'].splitlines()[-1]),taint_after=int(data['state-after.txt'].splitlines()[-1]),
        new_dpu_frame_done_timeouts=new.count(b'frame done timeout'),
        new_pingpong_done_timeouts=new.count(b'_dpu_encoder_phys_cmd_handle_ppdone_timeout'),
        new_kernel_warning_lines=new.count(b'WARNING:'),new_gpu_faults=new.count(b'*** gpu fault'),
        total_dpu_frame_done_timeouts=after.count(b'frame done timeout'),
        fbcon_unbound=True,slpi_offline_and_sensor_power_off=True)
    if label=='no_fbcon':
        assert data['config-before.sha256']==data['config-after.sha256']
        assert data['fbcon-unbind-exit.txt'].strip()==b'0'
        report.update(greetd_configuration_unchanged=True,initial_session_marker_preserved=True,
            original_phosh_session_started=bool(re.search(rb'\bcy122\s+.*\bphosh\b',data['processes-after-private.txt'])),
            runtime_change_only=True)
    else:
        report.update(output_wake_exit=int(data['output-wake-exit.txt']),
            output_read_exit=int(data['output-read-exit.txt']),screenshot_exit=int(data['screenshot-exit.txt']),
            output_enabled_before=b'Enabled: yes' in data['output-before.txt'],
            output_enabled_after=b'Enabled: yes' in data['output-after.txt'])
        if 'screenshot-private.png' in data:
            raw=data['screenshot-private.png'];assert raw[:8]==b'\x89PNG\r\n\x1a\n'
            width,height=struct.unpack_from('>II',raw,16)
            private=out/'display-wake15-screenshot-private.png';private.write_bytes(raw)
            report.update(screenshot_width=width,screenshot_height=height,screenshot_sha256=hashlib.sha256(raw).hexdigest(),screenshot_contents_private=True)
    reports[label]=report
report=dict(boot_checkpoint='reboot-audio-clean-15',actions=reports,
    physical_recovery_confirmed=False,physical_recovery_pending=True,
    permanent_display_fix_accepted=False,goal_complete=False)
(ref/'display-actions15-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
