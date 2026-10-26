from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile

out=Path('/mnt/e/edk2-samurai-out/kernel100')
files={}
with tarfile.open(out/'final-readonly-status.tar') as handle:
    for member in handle:
        if not member.isfile():continue
        parts=PurePosixPath(member.name).parts
        assert parts[0]=='k100-final-readonly-status' and '..' not in parts
        name=str(PurePosixPath(*parts[1:]));assert name not in files
        files[name]=handle.extractfile(member).read()
checked=set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);name=name.removeprefix('./')
    assert name not in checked and hashlib.sha256(files[name]).hexdigest()==digest
    checked.add(name)
assert checked==files.keys()-{'SHA256SUMS'}
state=files['state.txt'].decode().splitlines()
assert '#99 SMP PREEMPT' in state[0] and state[1]==(out/'runtime-boot-id-private.txt').read_text().strip()
assert state[3:]==['0','running']
assert b'wpa_state=COMPLETED\n' in files['wpa-status.txt'] and b'freq=5180\n' in files['wpa-status.txt']
payload=bytes.fromhex(re.search(r'command=0x0004 status=0x00 payload=([0-9a-f]+)',files['bt-info.txt'].decode())[1])
assert len(payload)==280 and int.from_bytes(payload[13:17],'little')&0x1b==0
assert re.search(r'^id=97 go=00 state=00 .*active=0 starts=0 stops=0 watchdog_stops=0 error=0\n$',files['haptics-status.txt'].decode())
assert len(files['nv-check.txt'].decode().splitlines())==6 and all(line.endswith(': OK') for line in files['nv-check.txt'].decode().splitlines())
assert files['persist-check.txt']==b'/dev/sda2: OK\n'
assert not re.search(r'^\s*\d+\s+root\s+\S+\s+(?:\{k100-|/tmp/k100-|scp -f |.*ff-(?:pulse|lifecycle))',files['processes.txt'].decode(),re.M)
dmesg=files['dmesg.txt'].decode()
baseline=json.loads((out/'checkpoint-validation.json').read_text())
assert dmesg.count('fatal error without message')==1
assert dmesg.count('Frame reassembly failed')==baseline['bt_frame_reassembly_error_count']
assert dmesg.count('failed to install key')==baseline['key_operation_timeout_warnings']
display=[float(x) for x in re.findall(r'^\[\s*([\d.]+)\].*frame done timeout',dmesg,re.M)]
owners=json.loads((out/'owner-recheck.json').read_text(encoding='utf-8-sig'))
assert not owners['eud_usbipd_attached'] and owners['matching_reader_flash_or_keepalive_processes']==0
report=dict(final_status_audit_pass=True,kernel_build=99,logical_stage=100,
    verified_private_files=len(checked),archive_sha256=hashlib.sha256((out/'final-readonly-status.tar').read_bytes()).hexdigest(),
    uptime_seconds=float(state[2].split()[0]),mpss_running=True,wpa_completed_5ghz=True,
    bluetooth_powered=False,haptics_standby=True,physical_vibration_confirmed=False,
    display_frame_done_timeout_uptimes=display,additional_display_timeouts=len(display)-len(baseline['display_frame_done_timeout_uptimes']),
    initial_auto_mpss_failure_preserved=True,no_additional_mpss_fatal=True,nv_and_persist_unchanged=True,
    no_test_transfer_or_reader_owner=True,taint=0,goal_complete=False)
(out/'final-status-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
