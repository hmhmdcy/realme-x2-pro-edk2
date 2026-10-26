from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel107';old=root/'reference/kernel106'
s=(old/'verify-tests.py').read_text().replace('kernel106','kernel107').replace('k106','k107')
header=s.split("names=['audio-runtime'",1)[0]
start=s.index('parts={n:h');end=s.index("assert fail['boot-finished']",start)
body=s[start:end]
script=header+'''names=['audio-runtime','first-radio-trace','playback','capture-dmic0','auto-network','24g-once','final-network']
allfiles={n:archive(n) for n in names}
r=allfiles['audio-runtime'];first=allfiles['first-radio-trace'];play=allfiles['playback'];cap=allfiles['capture-dmic0'];net=allfiles['auto-network'];band=allfiles['24g-once'];last=allfiles['final-network']
c=json.loads((out/'candidate-validation.json').read_text());state=r['state.txt'].decode().splitlines()
assert '#106 SMP PREEMPT' in state[0] and state[1]==(out/'runtime-boot-id-after-private.txt').read_text().strip()!=c['before_boot_id']
assert state[3]=='0' and state.count('running')==2 and first['boot-finished']==b'0\\n'
api=b'native_version_reply service4_api=7 service4_branch=0 service7_api=2 service7_branch=0\\n'
assert r['native-api.txt']==api and r['native-api-exit.txt']==b'0\\n'
trace=first['trace.txt'].decode()
assert len(re.findall(r'qrtr_endpoint_tx: node=0 wire_node=0 type=4 .*result=0',trace))>=3
assert 'result=-11' not in trace and 'samurai_qrtr_rx_drop:' not in trace
assert 'service=kernel/elf_loader offset=0 total=1 returned=1 result=0' in trace
assert 'phase=2 command=0x1292c token=0x1 opcode=0x0 bytes=0 status=0 result=0' in trace
for n,b in first.items():
    if n.endswith('-stats.txt'):assert all(int(v)==0 for v in re.findall(rb'^(?:overrun|commit overrun|dropped events):\\s*(\\d+)',b,re.M))
'''+body+'''
assert net['result.txt']==b'AUTOMATIC_FIRST_BOOT_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS\\n'
assert last['result.txt']==b'FINAL_AFTER_24G_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS\\n'
for f in [net,last]:
    assert b'freq=5180\\n' in f['status.txt'] and b'wpa_state=COMPLETED\\n' in f['status.txt']
    assert b'3 packets transmitted, 3 packets received, 0% packet loss' in f['gateway.txt']
    assert b'Example Domain' in f['http.txt'] and f['bt-class.txt']==b''
band_pass=band['result.txt']==b'SINGLE_24G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS\\n'
assert band_pass or band['result.txt']==b'SINGLE_24G_ATTEMPT_FAILED\\n'
if band_pass:
    assert re.search(rb'^freq=24[0-9][0-9]$',band['status.txt'],re.M) and b'wpa_state=COMPLETED\\n' in band['status.txt']
    assert b'3 packets transmitted, 3 packets received, 0% packet loss' in band['gateway.txt']
    assert b'Example Domain' in band['http.txt']
for f in allfiles.values():
    for n,b in f.items():
        if n.startswith('dmesg'):assert not re.search(rb'4080000\\.remoteproc: fatal|17300000\\.remoteproc: fatal|Unhandled context fault|unhandled context fault|Unexpected global fault|Kernel panic|Oops:',b)
        if n in ['nv-source-check.txt','nv-check.txt']:assert len(b.splitlines())==6 and all(l.endswith(b': OK') for l in b.splitlines())
report=dict(tests_archive_audit_pass=True,stage=107,kernel_build=106,archives={n+'.tar':sha((out/(n+'.tar')).read_bytes()) for n in names},private_files_verified=sum(len(f)-1 for f in allfiles.values()),native_api_query_pass=True,native_api_reply=api.decode().strip(),core_rebind_count=0,adsp_restart_count=0,microphones=[stats],microphone_signal_pass=True,microphone_acoustic_quality_confirmed=False,bounded_pcm_playback_pass=True,physical_speaker_sound_confirmed=False,boot_readbacks_match=True,full_boot_readback_sha256=c['full_backup_boot_sha256'],stock_dtbo_preserved=True,persist_preserved=True,nv_preserved=True,first_automatic_mpss_wifi_start_pass=True,first_hello_service_announcements_pass=True,trace_loss_count=0,manual_mpss_recovery_count=0,wifi_5g_auth_dhcp_dns_http_pass=True,wifi_24g_attempt_pass=band_pass,wifi_24g_long_term_fixed=False,wifi_long_term_stability_fixed=False,bluetooth_pair_or_connect=False,vibration_pulses=False,physical_vibration_deferred=True,goal_complete=False)
(out/'tests-validation.json').write_text(json.dumps(report,indent=2)+'\\n')
print(json.dumps({n:report[n] for n in ['tests_archive_audit_pass','native_api_query_pass','first_automatic_mpss_wifi_start_pass','first_hello_service_announcements_pass','manual_mpss_recovery_count','wifi_5g_auth_dhcp_dns_http_pass','wifi_24g_attempt_pass','microphones']},indent=2))
'''
assert not (ref/'verify-tests.py').exists();(ref/'verify-tests.py').write_text(script)
s=(old/'collect-checkpoint.sh').read_text().replace('k106','k107').replace('#105 SMP PREEMPT','#106 SMP PREEMPT')
a=s.index('for name in audio-runtime');b=s.index('; do',a)
s=s[:a]+'for name in audio-runtime first-radio-trace playback capture-dmic0 auto-network 24g-once final-network'+s[b:]
assert not (ref/'collect-checkpoint.sh').exists();(ref/'collect-checkpoint.sh').write_text(s)
print('STAGE107_SEVEN_ARCHIVE_AUTO_BOOT_AND_DUALBAND_VERIFIERS_PREPARED')
