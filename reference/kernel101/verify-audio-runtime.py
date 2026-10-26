from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel101')
sha=lambda b:hashlib.sha256(b).hexdigest()
files={}
with tarfile.open(out/'audio-runtime.tar') as tar:
    for m in tar:
        if not m.isfile():continue
        parts=PurePosixPath(m.name).parts
        assert parts[0]=='k101-audio-runtime' and '..' not in parts
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
assert '#100 SMP PREEMPT' in state[0]
assert state[1]==(out/'runtime-boot-id-after-private.txt').read_text().strip()!=candidate['before_boot_id']
assert state[3]=='0'
assert files['adsp-state.txt']==b'running\n'
assert re.search(r'^(native_version_reply service4_api=\d+ service4_branch=\d+ service7_api=\d+ service7_branch=\d+)\n$',files.get('native-api-reply.txt',b'').decode()) is not None or files['native-api-attributes.txt']==b'0\n'
assert files['boot-prefix.sha'].decode().split()[0]==candidate['boot_sha256']
parts={name:digest for digest,name in (line.split('  ',1) for line in files['partitions.sha'].decode().splitlines())}
assert parts['/tmp/k101-logdump-readback.img']==candidate['logdump_sha256']
assert files['persist-after.sha'].decode().split()[0]==(out/'persist-before.sha').read_text().split()[0]
assert len(files['nv-source-check.txt'].splitlines())==6 and all(line.endswith(b': OK') for line in files['nv-source-check.txt'].splitlines())
assert re.search(rb'^id=97 go=00 state=00 .*active=0 starts=0 stops=0 watchdog_stops=0 error=0\n$',files['haptics-status.txt'])
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel101')
deployment={name:digest for digest,name in (line.split('  ',1) for line in files['deployment.sha'].decode().splitlines())}
for name in ('samurai-wifi','samurai-radio-address','samurai-modem-remoteproc'):
    assert deployment['/usr/sbin/'+name]==sha((ref/name).read_bytes())
dmesg=files['dmesg.txt'].decode()
report=dict(runtime_archive_audit_pass=True,logical_stage=101,kernel_build=100,private_files=len(checked),
  archive_sha256=sha((out/'audio-runtime.tar').read_bytes()),uptime_seconds=float(state[2].split()[0]),
  adsp_running=True,adsp_native_version_reply_pass=files.get('native-api-exit.txt')==b'0\n',
  native_api_attribute_count=int(files['native-api-attributes.txt']),
  native_api_reply=files.get('native-api-reply.txt',b'').decode().strip(),
  mpss_state_at_capture=files['mpss-state.txt'].decode().strip(),
  automatic_wifi_exit=files.get('boot-finished',b'pending\n').decode().strip(),
  alsa_cards_empty=b'--- no soundcards ---' in files['alsa-cards.txt'],
  alsa_output_tested=False,amp_or_codec_enabled=False,boot_prefix_readback_matches=True,logdump_full_readback_matches=True,
  full_boot_readback_sha256=parts['/tmp/k101-boot-readback.img'],persist_unchanged=True,nv_unchanged=True,
  motor_standby=True,physical_vibration_confirmed=False,physical_vibration_deferred_by_user=True,
  kernel_taint=0,display_timeouts=dmesg.count('frame done timeout'),
  mpss_fatal_messages=len(re.findall(r'4080000\.remoteproc: fatal',dmesg)),
  adsp_fatal_messages=len(re.findall(r'17300000\.remoteproc: fatal',dmesg)),goal_complete=False)
(out/'runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'runtime-files-private.json').write_text(json.dumps({name:data.decode(errors='replace') for name,data in files.items() if not name.endswith('.bin')},indent=2)+'\n')
print(json.dumps(report,indent=2))
