from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile

out=Path('/mnt/e/edk2-samurai-out/kernel100')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference')
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
def cpio(path):
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

files=archive('checkpoint-final-retry1.tar','k100-checkpoint-final-retry1')
before=archive('preflash.tar','k100-preflash')
failure=archive('first-boot-failure.tar','k100-first-boot-failure')
recovery=archive('radio-recovery-first.tar','k100-radio-recovery-first')
network=archive('recovered-network.tar','k100-recovered-network')
candidate=json.loads((out/'candidate-validation.json').read_text())
previous=json.loads((out.parent/'kernel99/checkpoint-validation.json').read_text())
assert candidate['candidate_audit_pass'] and previous['checkpoint_audit_pass']
assert previous['motor_ff_electrical_and_close_kill_watchdog_pass']
for root,original in [('k100-first-boot-failure',failure),('k100-radio-recovery-first',recovery),('k100-recovered-network',network)]:
    assert all(files['tests/'+root+'/'+name]==data for name,data in original.items())
state=files['state.txt'].decode().splitlines()
assert '#99 SMP PREEMPT' in state[0] and state[1]!=candidate['before_boot_id']
assert state[1]==(out/'runtime-boot-id-private.txt').read_text().strip()
assert state[3:5]==['0','running'] and 'fb0' in state
assert files['boot-finished']==failure['boot-finished']==b'1\n'
assert files['samurai-wifi-boot.log']==failure['samurai-wifi-boot.log']
assert files['samurai-bluetooth-boot.log']==failure['samurai-bluetooth-boot.log']
assert 'PREPARE_OK\n' in failure['samurai-wifi-boot.log'].decode()
assert 'WIFI_READY\n' not in failure['samurai-wifi-boot.log'].decode()
waits=[(int(n),float(t)) for n,t in re.findall(r'WIFI_WAIT_SOURCES attempt=(\d+) uptime=([\d.]+)',failure['samurai-wifi-boot.log'].decode())]
assert [n for n,t in waits]==list(range(1,15))
assert recovery['result.txt']==b'BOUNDED_MANUAL_RECOVERY_AFTER_AUTO_MPSS_CRASH_PASS\n'
assert network['result.txt']==b'MANUAL_AFTER_CRASH_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS\n'
assert 'wpa_state=COMPLETED\n' in files['wpa-status.txt'].decode() and b'freq=5180\n' in files['wpa-status.txt']
assert '0% packet loss' in network['gateway.txt'].decode()
assert len(network['http.txt'])==577 and b'Example Domain' in network['http.txt']
assert files['address-status.txt']==b'wlan_cache=verified-this-boot\nbt_cache=verified-this-boot\n'
addresses={}
for kind in ('wlan','bt'):
    root='samurai-radio-address'
    query=files[f'{root}/current-{kind}'].decode().strip().split('/')[-1]
    assert re.fullmatch(r'query\.[A-Za-z0-9]{6}',query)
    assert files[f'{root}/{query}/boot-id'].decode().strip()==state[1]
    address=files[f'{root}/{query}/{kind}-mac-le.bin']
    raw=files[f'{root}/{query}/{kind}-dms-response.bin']
    assert len(address)==6 and any(address) and any(x!=255 for x in address) and address[5]&3==0
    assert len(raw)==24 and raw[:18]==bytes.fromhex('0201005c0011000204000000000010070006') and raw[18:]==address
    prior=before[f'{root}/current-{kind}'].decode().strip().split('/')[-1]
    assert address==before[f'{root}/{prior}/{kind}-mac-le.bin']
    addresses[kind]=address
assert bytes.fromhex(files['wlan-address.txt'].decode().strip().replace(':',''))==addresses['wlan'][::-1]
payload=bytes.fromhex(re.search(r'command=0x0004 status=0x00 payload=([0-9a-f]+)',files['bt-info.txt'].decode())[1])
assert len(payload)==280 and payload[:6]==addresses['bt'] and int.from_bytes(payload[13:17],'little')&0x1b==0
assert files['services/nv-source-hashes.txt']==before['nv-source-hashes.txt']==failure['nv-source-hashes.txt']
assert len(files['nv-source-check.txt'].decode().splitlines())==6
assert all(line.endswith(': OK') for line in files['nv-source-check.txt'].decode().splitlines())
assert files['persist-check.txt']==b'/dev/sda2: OK\n'
readback={name:digest for digest,name in (line.split('  ',1) for line in files['deployment-readback.txt'].decode().splitlines())}
assert readback['-']==candidate['boot_sha256'] and readback['/dev/sde11']==candidate['full_backup_boot_sha256']
assert readback['/dev/sde32']==candidate['logdump_sha256']
installed=cpio(out/'cpio-after')
assert readback['/init']==sha(installed['init'])
for name in ('samurai-wifi','samurai-bluetooth','samurai-radio-address','samurai-dms-mac-read','samurai-bt-address'):
    assert readback['/usr/sbin/'+name]==sha(installed['usr/sbin/'+name])
assert installed['usr/sbin/samurai-wifi']==(ref/'kernel99/samurai-wifi').read_bytes()
for name,data in installed.items():
    if name.startswith('lib/modules/samurai/') and name.endswith('.ko'):
        assert readback['/'+name]==sha(data)
assert re.search(r'^id=97 go=00 state=00 .*active=0 starts=0 stops=0 watchdog_stops=0 error=0\n$',files['haptics-status.txt'].decode())
fail_dmesg=failure['dmesg.txt'].decode();dmesg=files['dmesg.txt'].decode()
assert fail_dmesg.count('fatal error without message')==dmesg.count('fatal error without message')==1
assert recovery['dmesg-before.txt'].decode().count('fatal error without message')==recovery['dmesg-after.txt'].decode().count('fatal error without message')==1
initial_up=float(re.search(r'^\[\s*([\d.]+)\].*remote processor modem is now up',fail_dmesg,re.M)[1])
fatal_at=float(re.search(r'^\[\s*([\d.]+)\].*fatal error without message',fail_dmesg,re.M)[1])
assert 39<fatal_at-initial_up<41
assert not any(text in dmesg for text in ('failed to assign msa map permissions','failed to unmap msa permissions','haptics stopped; reset held after error'))
display_times=[float(x) for x in re.findall(r'^\[\s*([\d.]+)\].*frame done timeout',dmesg,re.M)]
frame_errors=re.findall(r'Frame reassembly failed \(-84\) phase=(\d+) baud=(\d+) chunk=(\d+) partial=(\d+) first=([0-9a-f]{2})',dmesg)
assert len(frame_errors)==dmesg.count('Frame reassembly failed') and all(x==('2','115200','1','0','00') for x in frame_errors)
reasons=re.findall(r'CTRL-EVENT-DISCONNECTED[^\n]*reason=(\d+)',files['services/wpa.log'].decode())
report=dict(checkpoint_audit_pass=True,logical_stage=100,kernel_build=99,
    checkpoint_sha256=sha((out/'checkpoint-final-retry1.tar').read_bytes()),verified_private_files=len(files)-1,
    private_archives={name:sha((out/name).read_bytes()) for name in ('first-boot-failure.tar','radio-recovery-first.tar','recovered-network.tar')},
    readiness_fix_embedded=True,all_source_wait_attempts=14,firmware_and_nv_prepare_pass=True,
    automatic_wifi_start_pass=False,automatic_bluetooth_address_pass=False,automatic_ap_connection=False,
    initial_mpss_crashed=True,first_modem_up_dmesg_seconds=initial_up,fatal_dmesg_seconds=fatal_at,
    fatal_after_modem_up_seconds=round(fatal_at-initial_up,3),crash_reason_message_available=False,
    mpss_crash_root_cause_resolved=False,manual_recovery_count=1,manual_recovery_pass=True,
    final_mpss_running=True,manual_5ghz_auth_dhcp_gateway_dns_http_pass=True,final_wpa_disconnect_reasons=reasons,
    final_bt_powered=False,bluetooth_pairing_connection_tested=False,
    haptics_warm_probe_standby_pass=True,previous_haptics_ff_electrical_lifecycle_proof_preserved=True,
    physical_vibration_confirmed=False,suspend_resume_tested=False,cold_power_boot_tested=False,
    display_frame_done_timeout_uptimes=display_times,bt_frame_reassembly_error_count=len(frame_errors),
    key_operation_timeout_warnings=dmesg.count('failed to install key'),key_wait_fix_applied=False,
    prior_two_ghz_unforced_drops_unresolved=True,nv_and_persist_unchanged=True,deployment_readback_verified=True,
    usb_large_transfer_failures_preserved=True,complete_backups_chunk_verified=True,goal_complete=False)
(out/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
