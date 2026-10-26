from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile
root=Path('/mnt/e/RealmeX2Pro edk2')
ref=root/'reference/kernel101'
out=Path('/mnt/e/edk2-samurai-out/kernel101')
sha=lambda b:hashlib.sha256(b).hexdigest()
def archive(path,prefix):
    files={}
    with tarfile.open(path) as tar:
        for m in tar:
            if not m.isfile():continue
            parts=PurePosixPath(m.name).parts
            assert parts[0]==prefix and '..' not in parts
            name=str(PurePosixPath(*parts[1:]));assert name not in files
            files[name]=tar.extractfile(m).read()
    checked=set()
    for line in files['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1);name=name.removeprefix('./')
        assert name not in checked and sha(files[name])==digest
        checked.add(name)
    assert checked==files.keys()-{'SHA256SUMS'}
    return files
files=archive(out/'checkpoint-retry1.tar','k101-checkpoint-retry1')
failure=archive(out/'first-boot-failure.tar','k101-first-boot-failure')
recovery=archive(out/'radio-recovery-first.tar','k101-radio-recovery-first')
network=archive(out/'recovered-network-retry1.tar','k101-recovered-network-retry1')
initial=archive(out/'audio-runtime.tar','k101-audio-runtime')
followup=archive(out/'gateway-followup.tar','k101-gateway-followup')
for name,original in [('k101-audio-runtime',initial),('k101-first-boot-failure',failure),
                      ('k101-radio-recovery-first',recovery),('k101-recovered-network-retry1',network)]:
    nested={p.removeprefix('tests/'+name+'/'):b for p,b in files.items() if p.startswith('tests/'+name+'/')}
    assert nested==original,name
assert files['result.txt']==b'ADSP_NATIVE_REPLY_AND_MANUAL_5G_CHECKPOINT_PASS\n'
assert files['boot-finished']==failure['boot-finished']==b'1\n'
assert files['samurai-wifi-boot.log']==failure['samurai-wifi-boot.log']
assert files['samurai-bluetooth-boot.log']==failure['samurai-bluetooth-boot.log']
assert recovery['result.txt']==b'BOUNDED_MANUAL_RECOVERY_AFTER_AUTO_MPSS_CRASH_PASS\n'
assert network['result.txt']==b'MANUAL_AFTER_CRASH_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS\n'
assert network['reconfigure.txt']==b'OK\n'
assert b'freq=5180\n' in network['status.txt'] and b'wpa_state=COMPLETED\n' in network['status.txt']
assert b'3 packets transmitted, 2 packets received, 33% packet loss' in network['gateway.txt']
assert b'Example Domain' in network['http.txt']
disconnects=re.findall(rb'CTRL-EVENT-DISCONNECTED[^\n]*',network['wpa.log'])
assert len(disconnects)==2
assert b'reason=7' in disconnects[0] and b'locally_generated=1' not in disconnects[0]
assert b'reason=3' in disconnects[1] and b'locally_generated=1' in disconnects[1]
assert b'5 packets transmitted, 5 packets received, 0% packet loss' in followup['gateway.txt']
for name in ('status-before.txt','status-after.txt'):
    assert b'freq=5180\n' in followup[name] and b'wpa_state=COMPLETED\n' in followup[name]
assert b'freq=2462\n' in files['tests/k101-recovered-network/status.txt']
assert b'wpa_state=COMPLETED\n' in files['tests/k101-recovered-network/status.txt']
assert 'tests/k101-recovered-network/result.txt' not in files
state=files['state.txt'].decode().splitlines()
assert '#100 SMP PREEMPT' in state[0]
assert state[1]==(out/'runtime-boot-id-after-private.txt').read_text().strip()
assert state[3:]==['0','running','running']
fs=followup['state.txt'].decode().splitlines()
assert fs[0]==state[1] and fs[2:]==['0','modem','running','adsp','running']
assert files['native-api.txt']==initial['native-api-reply.txt']==recovery['native-api-after.txt']
assert files['native-api.txt']==b'native_version_reply service4_api=7 service4_branch=0 service7_api=2 service7_branch=0\n'
assert b'--- no soundcards ---' in files['alsa-cards.txt']
assert 'qcom-q6core' in files['audio-bus.txt'].decode()
assert files['address-status.txt']==b'wlan_cache=verified-this-boot\nbt_cache=verified-this-boot\n'
assert 'BT_ADDRESS_VERIFIED index=0 powered=0 connectable=0 bondable=0' in recovery['bt-start.txt'].decode()
payload=bytes.fromhex(re.search(rb'command=0x0004 status=0x00 payload=([0-9a-f]+)',files['bt-info.txt'])[1].decode())
assert len(payload)==280 and int.from_bytes(payload[13:17],'little')&0x1b==0
assert re.search(rb'^id=97 go=00 state=00 .*active=0 starts=0 stops=0 watchdog_stops=0 error=0\n$',files['haptics-status.txt'])
assert len(files['nv-source-check.txt'].splitlines())==6 and all(line.endswith(b': OK') for line in files['nv-source-check.txt'].splitlines())
assert files['persist-after.sha'].decode().split()[0]==(out/'persist-before.sha').read_text().split()[0]
deployment={name:digest for digest,name in (line.split('  ',1) for line in files['deployment.sha'].decode().splitlines())}
candidate=json.loads((out/'candidate-validation.json').read_text())
assert deployment['/dev/sde32']==candidate['logdump_sha256']
runtime=json.loads((out/'runtime-validation.json').read_text())
assert deployment['/dev/sde11']==runtime['full_boot_readback_sha256']
boot=(out/'boot-k101-adsp.img').read_bytes()
old_boot=(out/'boot-partition-before.img').read_bytes()
assert len(boot)%4096==0
assert deployment['/dev/sde11']==sha(boot+old_boot[len(boot):])
ns={}
exec((root/'reference/kernel100/audit-kernel.py').read_text().split('before,after=')[0],ns)
installed=ns['cpio'](out/'cpio-after')
for path in ['/init']+[p for p in deployment if p.startswith('/usr/sbin/samurai-') or p.startswith('/lib/modules/samurai/')]:
    assert deployment[path]==sha(installed[path[1:]][1]),path
dt={}
exec((root/'reference/kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],dt)
exec((root/'reference/kernel73/dtb-canonical.py').read_text(),dt)
expected=dt['canonical'](dt['fdt_nodes']((out/'dtb-adsp').read_bytes()))
live=dt['canonical'](dt['fdt_nodes'](files['runtime-fdt.bin']))
for p in expected:
    if p.startswith('/soc@0/remoteproc@17300000') or p=='/reserved-memory/memory@9b200000':
        assert expected[p]==live[p],p
dmesg=files['dmesg.txt'].decode()
up=float(re.search(r'\[\s*([\d.]+)\].*remote processor modem is now up',dmesg)[1])
fatal=float(re.search(r'\[\s*([\d.]+)\].*4080000\.remoteproc: fatal',dmesg)[1])
assert 39<=fatal-up<=41
report=dict(checkpoint_audit_pass=True,logical_stage=101,kernel_build=100,verified_private_files=len(files)-1,
  checkpoint_sha256=sha((out/'checkpoint-retry1.tar').read_bytes()),uptime_seconds=float(state[2].split()[0]),
  adsp_first_auto_start_running=True,adsp_native_version_reply_pass=True,afe_api=7,asm_api=2,
  adsp_stayed_running_during_mpss_recovery=True,alsa_cards_empty=True,alsa_output_tested=False,
  automatic_wifi_start_pass=False,original_automatic_failure_preserved=True,
  first_mpss_up_seconds=up,first_mpss_fatal_seconds=fatal,first_mpss_uptime_seconds=round(fatal-up,6),
  mpss_fatal_count=len(re.findall(r'4080000\.remoteproc: fatal',dmesg)),
  adsp_fatal_count=len(re.findall(r'17300000\.remoteproc: fatal',dmesg)),
  bounded_manual_radio_recovery_pass=True,manual_5g_auth_dhcp_gateway_dns_http_pass=True,http_bytes=len(network['http.txt']),
  first_gateway_packets_sent=3,first_gateway_packets_received=2,first_gateway_packet_loss_percent=33,
  gateway_followup_packets_sent=5,gateway_followup_packets_received=5,gateway_followup_packet_loss_percent=0,
  gateway_followup_sha256=sha((out/'gateway-followup.tar').read_bytes()),gateway_followup_uptime_seconds=float(fs[1].split()[0]),
  additional_unforced_two_ghz_reason7_drop=True,controlled_five_ghz_switch_reason3_recorded=True,
  initial_wrong_band_profile_failure_preserved=True,initial_two_ghz_authentication_only=True,
  bluetooth_powered=False,bluetooth_connectable=False,bluetooth_bondable=False,bluetooth_discoverable=False,
  bluetooth_pairing_or_connection_tested=False,motor_standby=True,physical_vibration_confirmed=False,
  physical_vibration_deferred_by_user=True,additional_haptic_playbacks=0,
  full_boot_readback_sha256=deployment['/dev/sde11'],logdump_readback_matches=True,
  full_boot_prefix_and_unchanged_partition_tail_match=True,
  actual_firmware_adsp_nodes_match=True,all_ram_services_and_modules_match_cpio=True,nv_unchanged=True,persist_unchanged=True,
  display_timeouts=dmesg.count('frame done timeout'),bt_phase_errors=dmesg.count('Frame reassembly failed'),
  bt_error_phases=sorted(set(int(v) for v in re.findall(r'Frame reassembly failed[^\n]*phase=(\d+)',dmesg))),
  key_deletion_instrumented_this_boot=False,
  kernel_taint=0,cold_boot_tested=False,suspend_resume_tested=False,goal_complete=False)
(out/'checkpoint-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
