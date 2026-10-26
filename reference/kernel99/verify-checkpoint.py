from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile

out=Path('/mnt/e/edk2-samurai-out/kernel99')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel99')
sha=lambda data:hashlib.sha256(data).hexdigest()
def archive(path,root,manifest=True):
    files={}
    with tarfile.open(path) as handle:
        for member in handle:
            if not member.isfile(): continue
            parts=PurePosixPath(member.name).parts
            assert parts[0]==root and '..' not in parts
            name=str(PurePosixPath(*parts[1:]));assert name not in files
            files[name]=handle.extractfile(member).read()
    if manifest:
        checked=set()
        for line in files['SHA256SUMS'].decode().splitlines():
            digest,name=line.split('  ',1);name=name.removeprefix('./')
            assert name not in checked and sha(files[name])==digest
            checked.add(name)
        assert checked==files.keys()-{'SHA256SUMS'}
    return files

files=archive(out/'checkpoint-final.tar','k99-checkpoint-final')
before=archive(out/'preflash.tar','k99-preflash')
failure=archive(out/'first-boot-failure.tar','k99-first-boot-failure',False)
candidate=json.loads((out/'candidate-validation.json').read_text())
runtime=json.loads((out/'runtime-validation.json').read_text())
assert runtime['runtime_audit_pass']
state=files['state.txt'].decode().splitlines()
assert '#98 SMP PREEMPT' in state[0] and state[1]!=candidate['before_boot_id']
assert state[1]==(out/'runtime-boot-id-private.txt').read_text().strip()
assert state[3:5]==['0','running'] and 'fb0' in state
assert files['wpa-status.txt'].decode().find('wpa_state=COMPLETED\n')>=0 and b'freq=5180\n' in files['wpa-status.txt']
assert files['address-status.txt']==b'wlan_cache=verified-this-boot\nbt_cache=verified-this-boot\n'
assert files['samurai-wifi-boot.log']==failure['samurai-wifi-boot.log']==b''
assert files['samurai-bluetooth-boot.log']==failure['samurai-bluetooth-boot.log']
assert files['tests/k99-first-wifi-state/boot-finished']==b'1\n'
assert files['tests/k99-first-wifi-state/nv-source-hashes.txt']==b''
assert not any(name.startswith('tests/k99-first-wifi-state/nv/') for name in files)
assert files['boot-finished']==b'0\n' # Manual recovery; original auto-boot failure above is preserved.
for filename,root in [('haptics-initial-retry1.tar','k99-haptics-initial-retry1'),
    ('haptics-lifecycle.tar','k99-haptics-lifecycle'),('radio-ram-recovery.tar','k99-radio-ram-recovery'),
    ('restored-network-retry1.tar','k99-restored-network-retry1')]:
    original=archive(out/filename,root)
    assert all(files['tests/'+root+'/'+name]==data for name,data in original.items())
readback={name:digest for digest,name in (line.split('  ',1) for line in files['deployment-readback.txt'].decode().splitlines())}
assert readback['-']==candidate['boot_sha256'] and readback['/dev/sde32']==candidate['logdump_sha256']
assert readback['/usr/sbin/samurai-wifi']==sha((ref/'samurai-wifi').read_bytes())
def cpio_content(path):
    data=path.read_bytes();offset=0;result={}
    align=lambda n:(n+3)&~3
    while offset+110<=len(data):
        assert data[offset:offset+6]==b'070701'
        fields=[int(data[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
        start=offset+110;name=data[start:start+fields[11]-1].decode()
        start=align(start+fields[11]);content=data[start:start+fields[6]];offset=align(start+fields[6])
        if name=='TRAILER!!!':return result
        assert name not in result
        result[name]=content
    raise AssertionError('Missing CPIO trailer')
installed=cpio_content(out/'cpio-after')
assert installed['usr/sbin/samurai-wifi']==(ref.parent/'kernel97/samurai-wifi').read_bytes()
assert readback['/usr/sbin/samurai-wifi']!=sha(installed['usr/sbin/samurai-wifi'])
assert readback['/init']==sha(installed['init'])
for name in ('samurai-radio-address','samurai-bluetooth','samurai-dms-mac-read','samurai-bt-address'):
    assert readback['/usr/sbin/'+name]==sha(installed['usr/sbin/'+name])
for name,data in installed.items():
    if name.startswith('lib/modules/samurai/') and name.endswith('.ko'):
        assert readback['/'+name]==sha(data)
assert files['services/nv-source-hashes.txt']==before['nv-source-hashes.txt']
assert len(files['nv-source-check.txt'].decode().splitlines())==6
assert all(line.endswith(': OK') for line in files['nv-source-check.txt'].decode().splitlines())
assert files['persist-check.txt']==b'/dev/sda2: OK\n'
payload=bytes.fromhex(re.search(r'command=0x0004 status=0x00 payload=([0-9a-f]+)',files['bt-info.txt'].decode())[1])
assert len(payload)==280 and int.from_bytes(payload[13:17],'little')&0x1b==0
assert re.search(r'^id=97 go=00 state=00 .*active=0 starts=6 stops=6 watchdog_stops=1 error=0\n$',files['haptics-status.txt'].decode())
dmesg=files['dmesg.txt'].decode()
fail_dmesg=failure['dmesg.txt'].decode()
old_lines,new_lines=fail_dmesg.splitlines(),dmesg.splitlines()
overlap=old_lines.index(new_lines[0])
assert old_lines[overlap:]==new_lines[:len(old_lines)-overlap]
timeouts=[float(x) for x in re.findall(r'^\[\s*([\d.]+)\].*frame done timeout',dmesg,re.M)]
assert len(timeouts)==2
assert dmesg.count('Frame reassembly failed')==2
assert dmesg.count('Frame reassembly failed (-84) phase=2 baud=115200 chunk=1 partial=0 first=00')==2
assert 'failed to install key' not in dmesg and 'haptics stopped; reset held after error' not in dmesg
auto_exit=float(re.search(r'^\[\s*([\d.]+)\].*\[wifi\] startup exit=1',fail_dmesg,re.M)[1])
nv_gpt=float(re.search(r'^\[\s*([\d.]+)\].*sdf: sdf1',fail_dmesg,re.M)[1])
assert auto_exit<nv_gpt
report=dict(checkpoint_audit_pass=True,logical_stage=99,kernel_build=98,
    verified_private_files=len(files)-1,checkpoint_sha256=sha((out/'checkpoint-final.tar').read_bytes()),
    first_auto_failure_sha256=sha((out/'first-boot-failure.tar').read_bytes()),
    initial_dmesg_retained_in_first_failure_archive=True,initial_lines_rolled_out_of_final_ring=overlap,
    deployment_readback_verified=True,full_boot_readback_sha256=readback['/dev/sde11'],
    original_auto_wifi_failed=True,failed_worker_exit_dmesg_seconds=auto_exit,nv_lun_enumeration_dmesg_seconds=nv_gpt,
    readiness_race_observed=True,ram_service_delta_classified=True,readiness_fix_embedded_in_flash=False,
    manual_5ghz_network_pass=True,automatic_ap_connection=False,nv_and_persist_unchanged=True,
    motor_ff_electrical_and_close_kill_watchdog_pass=True,physical_vibration_confirmed=False,
    bluetooth_powered=False,bluetooth_pairing_connection_tested=False,
    display_frame_done_timeout_uptimes=timeouts,bt_frame_reassembly_error_count=2,
    key_wait_fix_applied=False,prior_two_ghz_unforced_drops_unresolved=True,cold_power_boot_tested=False,
    suspend_resume_tested=False,goal_complete=False)
(out/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
