from pathlib import Path, PurePosixPath
import hashlib, io, json, math, re, struct, tarfile, wave
root=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel104')
sha=lambda b:hashlib.sha256(b).hexdigest()
def archive(name,prefix):
    files={}
    with tarfile.open(out/name) as t:
        for m in t:
            assert not m.issym() and not m.islnk(),m.name
            if not m.isfile():continue
            parts=PurePosixPath(m.name).parts
            assert parts[0]==prefix and '..' not in parts and not m.name.startswith('/')
            n=str(PurePosixPath(*parts[1:]));assert n not in files
            files[n]=t.extractfile(m).read()
    checked=set()
    for line in files['SHA256SUMS'].decode().splitlines():
        digest,n=line.split('  ',1);n=n.removeprefix('./')
        assert n not in checked and sha(files[n])==digest;checked.add(n)
    assert checked==files.keys()-{'SHA256SUMS'}
    return files
runtime=archive('audio-runtime.tar','k104-audio-runtime')
play=archive('playback.tar','k104-playback')
captures=[archive(f'capture-dmic{n}.tar',f'k104-capture-dmic{n}') for n in range(3)]
net=archive('auto-network.tar','k104-auto-network')
failure=archive('first-boot-failure.tar','k104-first-boot-failure')
recovery=archive('radio-recovery-first.tar','k104-radio-recovery-first')
core=archive('core-rebind-once.tar','k104-core-rebind-once')
candidate=json.loads((out/'candidate-validation.json').read_text())
state=runtime['state.txt'].decode().splitlines()
assert '#103 SMP PREEMPT' in state[0]
assert state[1]==(out/'runtime-boot-id-after-private.txt').read_text().strip()!=candidate['before_boot_id']
assert state[3]=='0' and state.count('running')==1 and state.count('crashed')==1
assert b'Realme-X2Pro-samurai' in runtime['alsa.txt']
assert runtime['amplifiers.txt'].count(b'id=43')==2
assert runtime['boot-prefix.sha'].decode().split()[0]==candidate['boot_sha256']
parts={n:h for h,n in (l.split('  ',1) for l in runtime['partitions.sha'].decode().splitlines())}
boot=(out/'boot-k104-audio.img').read_bytes();previous=(out/'boot-partition-before.img').read_bytes()
assert parts['/tmp/k104-boot-readback.img']==sha(boot+previous[len(boot):])
assert parts['/tmp/k104-logdump-readback.img']==candidate['logdump_sha256']
assert runtime['persist-stock-dtbo.sha'].decode().splitlines()[0].split()[0]==(out/'persist-before.sha').read_text().split()[0]
with tarfile.open(out.parent/'kernel102/stock-audio-contract.tar') as t:
    stock=t.extractfile('k102-stock-audio-contract/dtbo-before.sha').read().decode().split()[0]
assert runtime['persist-stock-dtbo.sha'].decode().splitlines()[1].split()[0]==stock
assert len(runtime['nv-source-check.txt'].splitlines())==6 and all(l.endswith(b': OK') for l in runtime['nv-source-check.txt'].splitlines())
assert play['play-exit.txt']==b'0\n' and play['play-error.txt']==b''
for l in play['amp-after.txt'].decode().splitlines():assert re.search(r'id=43 .*global=00 amp=80 .*powered=0 muted=1 starts=1 stops=1 failed=0$',l),l
assert play['pcm-after.txt']==b'closed\n'
duration=float(play['end.txt'].split()[0])-float(play['start.txt'].split()[0]);assert 1.8<duration<4
stats=[]
for n,f in enumerate(captures):
    with wave.open(io.BytesIO(f['mic-private.wav'])) as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,48000)
        count=w.getnframes();data=w.readframes(count)
    values=struct.unpack('<'+'h'*count,data)
    live=f['dapm-live.txt'].decode();after=f['dapm-after.txt'].decode()
    active=lambda name:bool(re.search(r'^'+re.escape(name)+r': On\b',live,re.M))
    bias=1 if n<2 else 3
    s=dict(dmic=n,frames=count,seconds=count/48000,nonzero_samples=sum(v!=0 for v in values),
        minimum=min(values,default=0),maximum=max(values,default=0),distinct=len(set(values)),
        rms=math.sqrt(sum(v*v for v in values)/count) if count else 0,pcm_sha256=sha(data),
        steady_nonzero_samples=sum(v!=0 for v in values[24000:]),
        steady_distinct=len(set(values[24000:])),
        steady_minimum=min(values[24000:],default=0),steady_maximum=max(values[24000:],default=0),
        steady_rms=math.sqrt(sum(v*v for v in values[24000:])/len(values[24000:])) if len(values)>24000 else 0,
        steady_clipped_samples=sum(v in (-32768,32767) for v in values[24000:]),
        capture_exit=f['capture-exit.txt'].decode().strip(),pcm_closed=f['pcm-after.txt']==b'closed\n',
        dma_running=b'state: RUNNING\n' in f['pcm-live-status.txt'],
        dmic_power_on=active(f'DMIC{n}'),bias_power_on=active(f'MIC BIAS{bias}'),mclk_power_on=active('MCLK'),
        power_off_after_close=not re.search(r'^(?:DMIC'+str(n)+r'|MIC BIAS'+str(bias)+r'|MCLK): On\b',after,re.M),
        acoustic_quality_confirmed=False,signal_path_pass=False)
    s['signal_path_pass']=s['capture_exit']=='0' and s['dma_running'] and count>=240000 and s['steady_nonzero_samples']>10000 and s['steady_distinct']>32 and s['steady_clipped_samples']==0 and s['dmic_power_on'] and s['bias_power_on'] and s['mclk_power_on'] and s['power_off_after_close']
    assert s['pcm_closed'] and f['tainted.txt']==b'0\n'
    stats.append(s)
assert net['result.txt']==b'MANUAL_RECOVERY_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS\n'
assert b'freq=5180\n' in net['status.txt'] and b'wpa_state=COMPLETED\n' in net['status.txt']
assert net['bt-class.txt']==b'' and b'3 packets transmitted, 3 packets received, 0% packet loss' in net['gateway.txt']
assert b'Example Domain' in net['http.txt'] and len(net['http.txt'])==577
assert failure['boot-finished']==b'1\n' and b'crashed\n' in failure['state.txt']
assert recovery['result.txt']==b'BOUNDED_MANUAL_RECOVERY_AFTER_AUTO_MPSS_CRASH_PASS\n'
assert recovery['bt-class.txt']==b'' and recovery['state.txt'].decode().splitlines()[-1]=='running'
assert core['api-before-exit.txt']==core['api-after-exit.txt']==b'1\n'
assert core['remoteproc-after.txt']==b'modem\ncrashed\nadsp\nrunning\n'
for f in [runtime,play,net,failure]+captures:
    log=f['dmesg.txt']
    assert len(re.findall(rb'4080000\.remoteproc: fatal',log))==1
    assert not re.search(rb'17300000\.remoteproc: fatal|Unhandled context fault|unhandled context fault|Unexpected global fault|Kernel panic|Oops:',log)
assert recovery['dmesg-after.txt'].count(b'4080000.remoteproc: fatal')==1
api=runtime['native-api.txt'].decode().strip()
api_pass=runtime['native-api-exit.txt']==b'0\n' and bool(re.fullmatch(r'native_version_reply service4_api=\d+ service4_branch=\d+ service7_api=\d+ service7_branch=\d+',api))
names=['audio-runtime.tar','playback.tar','auto-network.tar','first-boot-failure.tar','radio-recovery-first.tar','core-rebind-once.tar']+[f'capture-dmic{n}.tar' for n in range(3)]
report=dict(tests_archive_audit_pass=True,stage=104,kernel_build=103,private_files_verified=sum(len(f)-1 for f in [runtime,play,net,failure,recovery,core]+captures),
 archives={n:sha((out/n).read_bytes()) for n in names},microphones=stats,
 native_api_query_pass=api_pass,native_api_reply=api if api_pass else None,native_api_query_failure_preserved=not api_pass,
 bounded_pcm_playback_pass=True,playback_seconds=duration,physical_speaker_sound_confirmed=False,
 microphone_acoustic_quality_confirmed=False,microphone_signal_pass=stats[0]['signal_path_pass'],
 boot_readbacks_match=True,full_boot_readback_sha256=parts['/tmp/k104-boot-readback.img'],
 stock_dtbo_preserved=True,persist_preserved=True,nv_preserved=True,
 first_automatic_mpss_wifi_start_pass=False,automatic_boot_failure_preserved=True,manual_mpss_recovery_executed=True,manual_mpss_recovery_count=1,
 wifi_5g_auth_dhcp_dns_http_pass=True,wifi_24g_fixed=False,wifi_long_term_stability_fixed=False,
 bluetooth_controller_removed=True,bluetooth_pair_or_connect=False,vibration_pulses=False,physical_vibration_deferred=True,
 adsp_restart_count=0,core_rebind_count=1,fatal_mpss_first_boot=1,fatal_adsp=0,goal_complete=False)
(out/'tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({n:report[n] for n in ('tests_archive_audit_pass','native_api_query_pass','microphones','bounded_pcm_playback_pass','wifi_5g_auth_dhcp_dns_http_pass')},indent=2))
