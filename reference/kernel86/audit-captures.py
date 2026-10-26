"""Verify captured device bytes; extract fixed flat members without path traversal."""
from pathlib import Path
import hashlib,json,re,tarfile
O=Path('/mnt/e/edk2-samurai-out/kernel86')
sha=lambda data:hashlib.sha256(data).hexdigest()
report={}
for group in ['preinstall','initial','native','prefinal','fault','initial-final','native-final']:
    archive=O/(group+'-raw.tar.gz')
    if not archive.exists():continue
    with tarfile.open(archive) as tar:
        raw={}
        for m in tar:
            prefix='tmp/k86-'+group+'-'
            assert m.isfile() and m.name.startswith(prefix) and '/' not in m.name[len(prefix):],m.name
            name=m.name.removeprefix('tmp/k86-');assert name not in raw
            data=tar.extractfile(m).read();raw[name]=data
            p=O/name
            if p.exists():assert p.read_bytes()==data
            else:p.write_bytes(data)
    hashes=raw[group+'-hashes.txt'].decode().splitlines()
    for line in hashes:
        digest,remote=line.split('  ',1)
        name=Path(remote).name.removeprefix('k86-')
        assert sha(raw[name])==digest,name
    assert len(raw)==len(hashes)+1
    state=raw[group+'-state.txt'].decode();log=raw[group+'-dmesg.txt'].decode()
    assert not re.search(r'\b(?:BUG:|Oops:)|Unable to handle kernel|dsi_err_worker',log)
    count=int(re.search(r'frame_done_cnt:(\d+)mode:',state)[1])
    assert re.search(r'underrun:\s+0 ',state)
    if group not in ['prefinal','fault']:assert count==0
    else:assert count>=1
    assert state.splitlines()[3]=='0'
    assert 'POWER_SUPPLY_CAPACITY=99' in state
    assert '08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405 ' in raw[group+'-partition-hashes.txt'].decode()
    config=raw.get(group+'-config.txt')
    expected='config-before' if group=='preinstall' else 'config-input'
    if config is not None:assert config==(O/expected).read_bytes()
    report[group]={'members':len(raw),'device_hashes':len(hashes),'archive_sha256':sha(archive.read_bytes()),
        'boot_id':state.splitlines()[0],'uptime_seconds':float(state.splitlines()[2].split()[0]),
        'taint':0,'frame_done_timeouts':count,'underruns':0,
        'configuration_file_matches':expected if config is not None else None}
    if group=='preinstall':
        assert state.startswith('f02d218a-cc7d-4b92-8858-c8eeaeab5777\n') and '#85 SMP PREEMPT' in state
        assert 'snapshot:count=1' in raw[group+'-trace-settings.txt'].decode()
        assert '60e183a6780945885a738ac1bd0c7e23ed41515bca662cb50a831ede3b57302b ' in raw[group+'-partition-hashes.txt'].decode()
        assert raw[group+'-registers.txt']==(O/'input-after-registers.txt').read_bytes()
    elif group in ['initial','native','prefinal','fault']:
        assert state.splitlines()[0]!='f02d218a-cc7d-4b92-8858-c8eeaeab5777' and '#86 SMP PREEMPT' in state
        candidate=json.loads((O/'candidate-validation.json').read_text())
        assert candidate['candidate_logdump_sha256'] in raw[group+'-partition-hashes.txt'].decode()
    else:
        assert state.splitlines()[0]!='32bf2d8f-8dde-47dc-9b88-e87db9e95198' and '#87 SMP PREEMPT' in state
        candidate=json.loads((O/'candidate-final-validation.json').read_text())
        assert candidate['candidate_logdump_sha256'] in raw[group+'-partition-hashes.txt'].decode()
(O/'capture-audit.json').write_text(json.dumps({'audit':'PASS','groups':report},indent=2)+'\n')
print(json.dumps(report,indent=2))
