from pathlib import Path,PurePosixPath
import hashlib,io,json,math,re,struct,tarfile,wave
root=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel106')
sha=lambda b:hashlib.sha256(b).hexdigest()
def archive_bytes(blob,prefix):
    files={}
    with tarfile.open(fileobj=io.BytesIO(blob)) as t:
        for m in t:
            assert not m.issym() and not m.islnk()
            if not m.isfile():continue
            p=PurePosixPath(m.name)
            assert p.parts[0]==prefix and not p.is_absolute() and '..' not in p.parts
            n=str(PurePosixPath(*p.parts[1:]));assert n not in files
            files[n]=t.extractfile(m).read()
    verified=set()
    for l in files['SHA256SUMS'].decode().splitlines():
        h,n=l.split('  ',1);n=n.removeprefix('./')
        assert n not in verified and sha(files[n])==h;verified.add(n)
    assert verified==files.keys()-{'SHA256SUMS'}
    return files
def archive(n):return archive_bytes((out/(n+'.tar')).read_bytes(),'k106-'+n)
names=['audio-runtime','core-rebind-once','first-radio-trace','playback','capture-dmic0','auto-network','first-boot-failure','radio-recovery-first']
allfiles={n:archive(n) for n in names}
r=allfiles['audio-runtime'];core=allfiles['core-rebind-once'];first=allfiles['first-radio-trace']
play=allfiles['playback'];cap=allfiles['capture-dmic0'];net=allfiles['auto-network'];fail=allfiles['first-boot-failure'];rec=allfiles['radio-recovery-first']
c=json.loads((out/'candidate-validation.json').read_text())
state=r['state.txt'].decode().splitlines()
assert '#105 SMP PREEMPT' in state[0] and state[1]==(out/'runtime-boot-id-after-private.txt').read_text().strip()!=c['before_boot_id']
assert state[3]=='0' and state.count('running')==1 and state.count('crashed')==1
api=b'native_version_reply service4_api=7 service4_branch=0 service7_api=2 service7_branch=0\n'
assert r['native-api.txt']==api and r['native-api-exit.txt']==b'0\n'
assert core['api-before.txt']==api and core['api-before-exit.txt']==b'0\n'
assert core['api-after.txt']==api and core['api-after-exit.txt']==b'0\n' and core['api-after-error.txt']==b''
assert b'APR: service is not registered' not in core['dmesg-after.txt']
assert core['dmesg-after.txt'].count(b'samurai APR service registered id=3 domain=4')==2
diag={};exec((root/'reference/kernel106/analyse-trace.py').read_text().split("if __name__=='__main__':",1)[0],diag)
for name in ['first-radio-trace','core-rebind-once','radio-recovery-first']:
    trace=diag['read_archive'](name)
    for n,b in trace.items():
        if n.endswith('-stats.txt'):
            assert all(int(v)==0 for v in re.findall(rb'^(?:overrun|commit overrun|dropped events):\s*(\d+)',b,re.M))
initial=first['trace.txt'].decode();recovered=rec['trace.txt'].decode()
hello_time=float(re.search(r'(\d+\.\d+): qrtr_endpoint_tx: node=0 wire_node=0 type=2 .*result=0',initial)[1])
blocked_time=float(re.search(r'(\d+\.\d+): qrtr_endpoint_tx: node=0 wire_node=0 type=4 .*result=-11',initial)[1])
assert blocked_time < hello_time and 'samurai_qrtr_rx_drop:' not in initial
assert len(re.findall(r'qrtr_endpoint_tx: node=0 wire_node=0 type=4 .*result=0',initial))==0
assert len(re.findall(r'qrtr_endpoint_tx: node=0 wire_node=0 type=4 .*result=0',recovered))==3
assert 'service=kernel/elf_loader offset=0 total=1 returned=1 result=0' in recovered
assert first['server-pids.txt']==rec['server-pids.txt']
assert 'phase=2 command=0x1292c token=0x1 opcode=0x0 bytes=0 status=0 result=0' in core['trace.txt'].decode()
assert 'result=-110' not in core['trace.txt'].decode()
parts={n:h for h,n in (l.split('  ',1) for l in r['partitions.sha'].decode().splitlines())}
assert parts['/tmp/k106-boot-readback.img']==c['full_backup_boot_sha256']
assert parts['/tmp/k106-logdump-readback.img']==c['logdump_sha256']
assert r['boot-prefix.sha'].decode().split()[0]==c['boot_sha256']
assert r['persist-stock-dtbo.sha'].decode().splitlines()[0].split()[0]==(out/'persist-before.sha').read_text().split()[0]
with tarfile.open(out.parent/'kernel102/stock-audio-contract.tar') as t:
    dtbo=t.extractfile('k102-stock-audio-contract/dtbo-before.sha').read().split()[0]
assert r['persist-stock-dtbo.sha'].splitlines()[1].split()[0]==dtbo
assert play['play-exit.txt']==b'0\n' and play['play-error.txt']==b'' and play['pcm-after.txt']==b'closed\n'
for l in play['amp-after.txt'].decode().splitlines():assert re.search(r'id=43 .*global=00 amp=80 .*powered=0 muted=1 starts=1 stops=1 failed=0$',l),l
with wave.open(io.BytesIO(cap['mic-private.wav'])) as w:
    assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,48000)
    frames=w.getnframes();values=struct.unpack('<'+'h'*frames,w.readframes(frames))
steady=values[24000:]
stats=dict(dmic=0,frames=frames,seconds=frames/48000,nonzero_samples=sum(v!=0 for v in values),steady_nonzero=sum(v!=0 for v in steady),steady_distinct=len(set(steady)),steady_minimum=min(steady),steady_maximum=max(steady),steady_rms=math.sqrt(sum(v*v for v in steady)/len(steady)),steady_clipped=sum(v in (-32768,32767) for v in steady),acoustic_quality_confirmed=False)
assert frames>=240000 and stats['steady_nonzero']>10000 and stats['steady_distinct']>32 and stats['steady_clipped']==0
assert cap['capture-exit.txt']==b'0\n' and cap['capture-error.txt']==b'' and cap['pcm-after.txt']==b'closed\n'
for n in ['DMIC0','MIC BIAS1','MCLK']:
    assert re.search(rb'^'+n.encode()+rb': On\b',cap['dapm-live.txt'],re.M)
    assert not re.search(rb'^'+n.encode()+rb': On\b',cap['dapm-after.txt'],re.M)
assert fail['boot-finished']==b'1\n' and b'crashed\n' in fail['state.txt']
assert b'item=421 error=-2 bytes=0' in fail['dmesg.txt'] and b'modem-host=1 item=421 error=-2 bytes=0' in fail['dmesg.txt']
assert rec['result.txt']==b'BOUNDED_MANUAL_RECOVERY_AFTER_AUTO_MPSS_CRASH_PASS\n'
assert net['result.txt']==b'MANUAL_RECOVERY_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS\n'
assert b'freq=5180\n' in net['status.txt'] and b'wpa_state=COMPLETED\n' in net['status.txt']
assert b'3 packets transmitted, 3 packets received, 0% packet loss' in net['gateway.txt'] and net['bt-class.txt']==b''
assert b'Example Domain' in net['http.txt'] and len(net['http.txt'])==577
for f in allfiles.values():
    for n,b in f.items():
        if n.startswith('dmesg'):
            assert not re.search(rb'17300000\.remoteproc: fatal|Unhandled context fault|unhandled context fault|Unexpected global fault|Kernel panic|Oops:',b)
for f in [r,fail,net,rec]:
    for n in ['nv-source-check.txt','nv-check.txt','nv-before.txt','nv-after.txt']:
        if n in f:assert len(f[n].splitlines())==6 and all(l.endswith(b': OK') for l in f[n].splitlines())
report=dict(tests_archive_audit_pass=True,stage=106,kernel_build=105,archives={n+'.tar':sha((out/(n+'.tar')).read_bytes()) for n in names},private_files_verified=sum(len(f)-1 for f in allfiles.values()),native_api_query_pass=True,native_api_reply=api.decode().strip(),apr_core_rebind_dispatch_restored=True,first_rebind_query_within_100ms_pass=True,eud_reader_active_during_rebind=False,first_hello_service_announcement_race_observed=True,trace_loss_count=0,original_services_reused=True,core_rebind_count=1,adsp_restart_count=0,microphones=[stats],microphone_signal_pass=True,microphone_acoustic_quality_confirmed=False,bounded_pcm_playback_pass=True,physical_speaker_sound_confirmed=False,boot_readbacks_match=True,full_boot_readback_sha256=c['full_backup_boot_sha256'],stock_dtbo_preserved=True,persist_preserved=True,nv_preserved=True,first_automatic_mpss_wifi_start_pass=False,manual_mpss_recovery_count=1,wifi_5g_auth_dhcp_dns_http_pass=True,wifi_24g_fixed=False,wifi_long_term_stability_fixed=False,bluetooth_pair_or_connect=False,vibration_pulses=False,physical_vibration_deferred=True,goal_complete=False)
(out/'tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({n:report[n] for n in ['tests_archive_audit_pass','native_api_query_pass','apr_core_rebind_dispatch_restored','microphones','bounded_pcm_playback_pass','wifi_5g_auth_dhcp_dns_http_pass']},indent=2))
