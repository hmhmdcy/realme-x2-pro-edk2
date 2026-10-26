from pathlib import Path,PurePosixPath
import hashlib,io,json,math,re,struct,tarfile,wave
root=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel103')
sha=lambda b:hashlib.sha256(b).hexdigest()
def archive(name,prefix):
    files={}
    with tarfile.open(out/name) as t:
        for m in t:
            if not m.isfile():continue
            parts=PurePosixPath(m.name).parts
            assert parts[0]==prefix and '..' not in parts
            n=str(PurePosixPath(*parts[1:]));assert n not in files
            files[n]=t.extractfile(m).read()
    checked=set()
    for line in files['SHA256SUMS'].decode().splitlines():
        digest,n=line.split('  ',1);n=n.removeprefix('./')
        assert n not in checked and sha(files[n])==digest;checked.add(n)
    assert checked==files.keys()-{'SHA256SUMS'}
    return files
runtime=archive('audio-runtime-retry1.tar','k103-audio-runtime-retry1')
play=archive('playback.tar','k103-playback')
cap=archive('capture.tar','k103-capture')
dmic=archive('capture-dmic0.tar','k103-capture-dmic0')
net=archive('auto-network.tar','k103-auto-network')
core=archive('core-rebind-once.tar','k103-core-rebind-once')
candidate=json.loads((out/'candidate-validation.json').read_text())
state=runtime['state.txt'].decode().splitlines()
assert '#102 SMP PREEMPT' in state[0] and state[1]==(out/'runtime-boot-id-after-private.txt').read_text(encoding='utf-8-sig').strip()!=candidate['before_boot_id']
assert state[3]=='0' and state.count('running')==2
assert runtime['native-api-exit.txt']==b'1\n'
assert b'Realme-X2Pro-samurai' in runtime['alsa.txt']
assert runtime['amplifiers.txt'].count(b'id=43')==2
assert runtime['boot-prefix.sha'].decode().split()[0]==candidate['boot_sha256']
parts={n:h for h,n in (l.split('  ',1) for l in runtime['partitions.sha'].decode().splitlines())}
boot=(out/'boot-k103-audio.img').read_bytes();previous=(out/'boot-partition-before.img').read_bytes()
assert parts['/tmp/k103-boot-readback.img']==sha(boot+previous[len(boot):])
assert parts['/tmp/k103-logdump-readback.img']==candidate['logdump_sha256']
assert runtime['persist-stock-dtbo.sha'].decode().splitlines()[0].split()[0]==(out/'persist-before.sha').read_text().split()[0]
with tarfile.open(out.parent/'kernel102/stock-audio-contract.tar') as t:
    stock=t.extractfile('k102-stock-audio-contract/dtbo-before.sha').read().decode().split()[0]
assert runtime['persist-stock-dtbo.sha'].decode().splitlines()[1].split()[0]==stock
assert len(runtime['nv-source-check.txt'].splitlines())==6 and all(l.endswith(b': OK') for l in runtime['nv-source-check.txt'].splitlines())
assert runtime['boot-finished']==b'0\n'
assert play['play-exit.txt']==b'0\n' and play['play-error.txt']==b''
for l in play['amp-after.txt'].decode().splitlines():assert re.search(r'id=43 .*global=00 amp=80 .*powered=0 muted=1 starts=1 stops=1 failed=0$',l),l
assert play['pcm-after.txt']==b'closed\n'
play_seconds=float(play['end.txt'].split()[0])-float(play['start.txt'].split()[0])
assert 1.8<play_seconds<4
assert cap['capture-exit.txt']==b'0\n' and cap['capture-error.txt']==b''
assert cap['pcm-after.txt']==b'closed\n' and b'state: RUNNING\n' in cap['pcm-live-status.txt']
assert b'channels: 1\nrate: 48000 (48000/1)\n' in cap['pcm-live-hw-params.txt']
assert int(re.search(rb'hw_ptr\s*:\s*(\d+)',cap['pcm-live-status.txt'])[1])>40000
with wave.open(io.BytesIO(cap['mic-private.wav'])) as w:
    assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,48000)
    frames=w.getnframes();data=w.readframes(frames)
values=struct.unpack('<'+'h'*frames,data)
stats=dict(frames=frames,seconds=frames/48000,nonzero_samples=sum(v!=0 for v in values),min=min(values),max=max(values),
           mean=sum(values)/frames,rms=math.sqrt(sum(v*v for v in values)/frames),distinct=len(set(values)),pcm_sha256=sha(data))
assert frames==241920 and stats['nonzero_samples']==0 and stats['distinct']==1,stats
with wave.open(io.BytesIO(dmic['mic-private.wav'])) as w:
    assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,48000)
    dframes=w.getnframes();ddata=w.readframes(dframes)
dvalues=struct.unpack('<'+'h'*dframes,ddata)
dstats=dict(frames=dframes,seconds=dframes/48000,nonzero_samples=sum(v!=0 for v in dvalues),min=min(dvalues),max=max(dvalues),
            mean=sum(dvalues)/dframes,rms=math.sqrt(sum(v*v for v in dvalues)/dframes),distinct=len(set(dvalues)),pcm_sha256=sha(ddata))
assert dframes==241920 and dmic['capture-exit.txt']==b'0\n' and dmic['capture-error.txt']==b''
assert dmic['pcm-after.txt']==b'closed\n' and b'state: RUNNING\n' in dmic['pcm-live-status.txt']
print('DMIC0 signal statistics:',json.dumps(dstats))
assert net['result.txt']==b'AUTO_BOOT_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS\n'
assert b'freq=5180\n' in net['status.txt'] and b'wpa_state=COMPLETED\n' in net['status.txt']
assert net['bt-class.txt']==b'' and b'3 packets transmitted, 3 packets received, 0% packet loss' in net['gateway.txt']
assert b'Example Domain' in net['http.txt'] and len(net['http.txt'])==577
assert core['api-before-exit.txt']==core['api-after-exit.txt']==b'1\n'
assert b'Realme-X2Pro-samurai' in core['alsa-after.txt'] and core['remoteproc-after.txt']==b'modem\nrunning\nadsp\nrunning\n'
for f in (runtime,play,cap,dmic,net,core):
    d=f.get('dmesg.txt',f.get('dmesg-after.txt',b''))
    assert not re.search(rb'4080000\.remoteproc: fatal|17300000\.remoteproc: fatal|Unhandled context fault|unhandled context fault|Unexpected global fault|Kernel panic|Oops:',d)
report=dict(tests_archive_audit_pass=True,stage=103,kernel_build=102,private_files_verified=sum(len(f)-1 for f in (runtime,play,cap,dmic,net,core)),
 archives={n:sha((out/n).read_bytes()) for n in ('audio-runtime-retry1.tar','playback.tar','capture.tar','capture-dmic0.tar','auto-network.tar','core-rebind-once.tar')},
 alsa_card_registered=True,wcd_chip_major='0x108',wcd_chip_minor='0x1',dual_max98937_revision='0x43',
 bounded_pcm_playback_pass=True,playback_seconds=play_seconds,playback_rate=48000,playback_channels=2,playback_peak_dbfs=-48.16,
 both_amp_start_stop_balanced=True,amp_global_disabled_after_close=True,finite_mic_dma_capture_pass=True,microphone_amic1=stats,microphone_dmic0=dstats,
 microphone_signal_pass=dstats['nonzero_samples']>10000 and dstats['distinct']>32,microphone_route_builtin_correct=False,
 physical_speaker_sound_confirmed=False,microphone_quality_confirmed=False,headphone_or_jack_tested=False,
 native_api_query_initial_pass=False,native_api_after_one_core_rebind_pass=False,core_rebind_count=1,dsp_restart_count=0,
 native_version_query_failure_unresolved=True,core_cache_only_cause_proven=False,
 boot_readbacks_match=True,full_boot_readback_sha256=parts['/tmp/k103-boot-readback.img'],stock_dtbo_preserved=True,persist_preserved=True,nv_preserved=True,
 first_automatic_mpss_wifi_start_pass=True,manual_mpss_recovery_executed=False,wifi_5g_auth_dhcp_dns_http_pass=True,gateway_sent=3,gateway_received=3,
 bluetooth_controller_removed=True,bluetooth_pair_or_connect=False,motor_physical_feedback_deferred=True,goal_complete=False)
(out/'tests-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({n:report[n] for n in ('tests_archive_audit_pass','bounded_pcm_playback_pass','finite_mic_dma_capture_pass','microphone_signal_pass','wifi_5g_auth_dhcp_dns_http_pass','native_version_query_failure_unresolved')},indent=2))
