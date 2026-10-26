from pathlib import Path,PurePosixPath
import hashlib,json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel102')
root=Path('/mnt/e/RealmeX2Pro edk2')
sha=lambda b:hashlib.sha256(b).hexdigest()
files={}
with tarfile.open(out/'audio-runtime-retry1.tar') as tar:
    for m in tar:
        if not m.isfile():continue
        parts=PurePosixPath(m.name).parts
        assert parts[0]=='k102-audio-runtime-retry1' and '..' not in parts
        name=str(PurePosixPath(*parts[1:]));assert name not in files
        files[name]=tar.extractfile(m).read()
checked=set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);name=name.removeprefix('./')
    assert name not in checked and sha(files[name])==digest
    checked.add(name)
assert checked==files.keys()-{'SHA256SUMS'}
candidate=json.loads((out/'candidate-validation.json').read_text())
state=files['state.txt'].decode().splitlines()
assert '#101 SMP PREEMPT' in state[0]
assert state[1]==(out/'runtime-boot-id-after-private.txt').read_text().strip()!=candidate['before_boot_id']
assert state[3]=='0'
assert files['adsp-state.txt']==b'running\n'
assert files['native-api-attributes.txt']==b'1\n' and files['native-api-exit.txt']==b'0\n'
assert files['native-api-reply.txt']==b'native_version_reply service4_api=7 service4_branch=0 service7_api=2 service7_branch=0\n'
assert files['boot-prefix.sha'].decode().split()[0]==candidate['boot_sha256']
parts={name:digest for digest,name in (line.split('  ',1) for line in files['partitions.sha'].decode().splitlines())}
assert parts['/tmp/k102-logdump-readback-retry1.img']==candidate['logdump_sha256']
boot=(out/'boot-k102-audio.img').read_bytes();prev=(out/'boot-partition-before.img').read_bytes()
assert parts['/tmp/k102-boot-readback-retry1.img']==sha(boot+prev[len(boot):])
assert files['persist-after.sha'].decode().split()[0]==(out/'persist-before.sha').read_text().split()[0]
assert len(files['nv-source-check.txt'].splitlines())==6 and all(l.endswith(b': OK') for l in files['nv-source-check.txt'].splitlines())
assert re.search(rb'^id=97 go=00 state=00 .*active=0 starts=0 stops=0 watchdog_stops=0 error=0\n$',files['haptics-status.txt'])
deployment={name:digest for digest,name in (line.split('  ',1) for line in files['deployment.sha'].decode().splitlines())}
for name in ('samurai-wifi','samurai-radio-address','samurai-modem-remoteproc'):
    assert deployment['/usr/sbin/'+name]==sha((root/'reference/kernel101'/name).read_bytes())
dtbo=json.loads((out/'stock-overlay-nodes-private.json').read_text()) # evidence exists; binary remains private
with tarfile.open(out/'stock-audio-contract.tar') as tar:
    before=tar.extractfile('k102-stock-audio-contract/dtbo-before.sha').read().decode().split()[0]
assert files['stock-dtbo-after.sha'].decode().split()[0]==before
dmesg=files['dmesg.txt'].decode();bus=files['codec-bus.txt'].decode();pins=files['pinmux.txt'].decode()
wcd=re.findall(r'WCD934x chip id major (0x[0-9a-f]+), minor (0x[0-9a-f]+)',dmesg)
amps=re.findall(r'max98927 (\d+-00(?:39|3a)): MAX98927 revisionID: (0x[0-9A-Fa-f]+)',dmesg)
report=dict(runtime_archive_audit_pass=True,logical_stage=102,kernel_build=101,private_files=len(checked),
 archive_sha256=sha((out/'audio-runtime-retry1.tar').read_bytes()),uptime_seconds=float(state[2].split()[0]),
 adsp_running=True,adsp_native_version_reply_pass=True,native_api_reply=files['native-api-reply.txt'].decode().strip(),
 mpss_state_at_capture=files['mpss-state.txt'].decode().strip(),automatic_wifi_exit=files.get('boot-finished',b'pending\n').decode().strip(),
 wcd_chip_id_replies=wcd,amp_revision_replies=amps,wcd_platform_codec_bound='wcd934x-codec.' in bus,
 alsa_cards_empty=b'--- no soundcards ---' in files['alsa-cards.txt'],alsa_output_tested=False,
 pcm_or_speaker_output_tested=False,boot_prefix_readback_matches=True,full_boot_readback_matches=True,
 logdump_full_readback_matches=True,full_boot_readback_sha256=parts['/tmp/k102-boot-readback-retry1.img'],
 stock_dtbo_unchanged=True,persist_unchanged=True,nv_unchanged=True,motor_standby=True,
 physical_vibration_deferred_by_user=True,kernel_taint=0,display_timeouts=dmesg.count('frame done timeout'),
 mpss_fatal_messages=len(re.findall(r'4080000\.remoteproc: fatal',dmesg)),
 adsp_fatal_messages=len(re.findall(r'17300000\.remoteproc: fatal',dmesg)),
 smmu_fault_lines=[l for l in dmesg.splitlines() if re.search('unhandled context fault|Unexpected global fault|Unhandled context fault',l)],goal_complete=False)
(out/'runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'runtime-files-private.json').write_text(json.dumps({n:b.decode(errors='replace') for n,b in files.items() if not n.endswith('.bin')},indent=2)+'\n')
print(json.dumps(report,indent=2))
