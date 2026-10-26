from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile

out=Path('/mnt/e/edk2-samurai-out/kernel100')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel99')
sha=lambda data:hashlib.sha256(data).hexdigest()
def archive(filename,root):
    files={}
    with tarfile.open(out/filename) as handle:
        for member in handle:
            if not member.isfile():continue
            parts=PurePosixPath(member.name).parts
            assert parts[0]==root and '..' not in parts
            name=str(PurePosixPath(*parts[1:]));assert name not in files
            files[name]=handle.extractfile(member).read()
    checked=set()
    for line in files['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1);name=name.removeprefix('./')
        assert name not in checked and sha(files[name])==digest
        checked.add(name)
    assert checked==files.keys()-{'SHA256SUMS'}
    return files

files=archive('automatic-start.tar','k100-automatic-start')
before=archive('preflash.tar','k100-preflash')
candidate=json.loads((out/'candidate-validation.json').read_text())
assert files['result.txt']==b'AUTOMATIC_ALL_SOURCE_READINESS_AND_HAPTICS_STANDBY_PASS\n'
state=files['state.txt'].decode().splitlines()
assert '#99 SMP PREEMPT' in state[0] and state[1]!=candidate['before_boot_id']
assert state[3:5]==['0','running'] and 'fb0' in state
assert files['boot-finished']==b'0\n'
assert sha((ref/'samurai-wifi').read_bytes()) in files['service-hash.txt'].decode()
wait_log=files['samurai-wifi-boot.log'].decode()
assert 'PREPARE_OK\n' in wait_log and 'WIFI_READY\n' in wait_log
assert 'WIFI_SOURCE_WAIT_TIMEOUT' not in wait_log and 'startup exit=1' not in files['dmesg.txt'].decode()
waits=[(int(n),float(t)) for n,t in re.findall(r'WIFI_WAIT_SOURCES attempt=(\d+) uptime=([\d.]+)',wait_log)]
assert all(1<=n<=60 for n,t in waits)
assert 'RADIO_ADDRESS_QUERY_VERIFIED kind=wlan ' in wait_log
assert 'RADIO_ADDRESS_QUERY_VERIFIED kind=bt ' in files['samurai-bluetooth-boot.log'].decode()
addresses={}
for kind in ('wlan','bt'):
    root='radio-address-before-manual'
    query=files[f'{root}/current-{kind}'].decode().strip().split('/')[-1]
    assert re.fullmatch(r'query\.[A-Za-z0-9]{6}',query)
    assert files[f'{root}/{query}/boot-id'].decode().strip()==state[1]
    address=files[f'{root}/{query}/{kind}-mac-le.bin']
    raw=files[f'{root}/{query}/{kind}-dms-response.bin']
    assert len(address)==6 and any(address) and any(x!=255 for x in address) and address[5]&3==0
    assert len(raw)==24 and raw[:18]==bytes.fromhex('0201005c0011000204000000000010070006') and raw[18:]==address
    prior=before[f'samurai-radio-address/current-{kind}'].decode().strip().split('/')[-1]
    assert address==before[f'samurai-radio-address/{prior}/{kind}-mac-le.bin']
    addresses[kind]=address
assert bytes.fromhex(files['wlan-before-manual.txt'].decode().strip().replace(':',''))==addresses['wlan'][::-1]
payload=bytes.fromhex(re.search(r'command=0x0004 status=0x00 payload=([0-9a-f]+)',files['bt-before-manual.txt'].decode())[1])
assert len(payload)==280 and payload[:6]==addresses['bt'] and int.from_bytes(payload[13:17],'little')&0x1b==0
assert re.search(r'^id=97 go=00 state=00 .*active=0 starts=0 stops=0 watchdog_stops=0 error=0\n$',files['haptics-status.txt'].decode())
assert 'AW8697 id=97 standby' in files['dmesg.txt'].decode()
assert len(files['nv-check.txt'].decode().splitlines())==6 and all(line.endswith(': OK') for line in files['nv-check.txt'].decode().splitlines())
report=dict(automatic_start_audit_pass=True,logical_stage=100,kernel_build=99,
    archive_sha256=sha((out/'automatic-start.tar').read_bytes()),verified_private_files=len(files)-1,
    automatic_wifi_and_bluetooth_driver_start=True,automatic_ap_connection=False,
    sources_wait_log_count=len(waits),sources_wait_attempts=[n for n,t in waits],
    readiness_fix_embedded=True,manual_radio_recovery_required=False,
    independent_addresses_observed_before_manual_query=True,addresses_cross_warm_boot_equal=True,
    bluetooth_powered=False,bluetooth_pairing_connection_tested=False,
    haptics_chip_probe_and_standby_after_warm_reboot=True,physical_vibration_confirmed=False,
    display_frame_done_timeout_count=files['dmesg.txt'].decode().count('frame done timeout'),
    bt_frame_reassembly_error_count=files['dmesg.txt'].decode().count('Frame reassembly failed'),
    cold_power_boot_tested=False,suspend_resume_tested=False,goal_complete=False)
(out/'automatic-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
