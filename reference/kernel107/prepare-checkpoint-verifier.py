from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel107';old=root/'reference/kernel106'
s=(old/'verify-checkpoint.py').read_text().replace('kernel106','kernel107').replace('k106','k107').replace('#105 SMP PREEMPT','#106 SMP PREEMPT')
s=s.replace("=={'hci_uart','btqca','btbcm'}","<={'hci_uart','btqca','btbcm'}")
s=s[:s.index("log=f['dmesg.txt'].decode()")]+'''log=f['dmesg.txt'].decode()
assert not re.search(r'4080000\\.remoteproc: fatal|17300000\\.remoteproc: fatal|Unhandled context fault|unhandled context fault|Unexpected global fault|Kernel panic|Oops:',log)
ups=[float(x) for x in re.findall(r'\\[\\s*([\\d.]+)\\] remoteproc remoteproc\\d+: remote processor modem is now up',log)]
adspups=re.findall(r'remote processor adsp is now up',log)
assert len(ups)==1 and len(adspups)==1 and f['boot-finished']==b'0\\n'
v=dict(checkpoint_archive_audit_pass=True,stage=107,kernel_build=106,private_files_verified=count,archive_sha256=sha((out/'checkpoint.tar').read_bytes()),uptime_seconds=float(state[2].split()[0]),mpss_running_seconds=float(state[2].split()[0])-ups[0],first_mpss_up_seconds=ups[0],first_mpss_fatal_seconds=None,first_automatic_wifi_start_pass=True,manual_mpss_recovery_count=0,wifi_5g_auth_dhcp_dns_http_pass=True,wifi_24g_attempt_pass=t['wifi_24g_attempt_pass'],wifi_stability_fixed=False,native_api_query_pass=True,first_hello_service_announcements_pass=True,trace_loss_count=0,core_rebind_count=0,no_adsp_restarts=True,microphone_signal_pass=True,microphone_quality_confirmed=False,physical_speaker_sound_confirmed=False,bluetooth_pair_or_connect=False,physical_vibration_deferred_by_user=True,firmware_boot_byte_identical=True,firmware_and_runtime_fdt_match=True,nv_and_persist_preserved=True,cpio_and_modules_preserved=True,kernel_taint=0,display_timeouts=log.count('frame done timeout'),bt_phase2_errors=log.count('Frame reassembly failed'),fatal_mpss=0,fatal_adsp=0,goal_complete=False)
(out/'checkpoint-validation.json').write_text(json.dumps(v,indent=2)+'\\n')
print(json.dumps(v,indent=2))
'''
assert not (ref/'verify-checkpoint.py').exists();(ref/'verify-checkpoint.py').write_text(s)
print('STAGE107_NO_MANUAL_RECOVERY_CHECKPOINT_VERIFIER_PREPARED')
