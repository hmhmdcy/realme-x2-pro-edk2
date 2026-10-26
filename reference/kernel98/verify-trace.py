from pathlib import Path, PurePosixPath
import hashlib, json, re, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel98')
files = {}
with tarfile.open(out/'trace-connectivity.tar') as archive:
    for member in archive:
        if not member.isfile(): continue
        parts=PurePosixPath(member.name).parts
        assert parts[0]=='k98-trace-connectivity' and '..' not in parts
        name=str(PurePosixPath(*parts[1:]));assert name not in files
        files[name]=archive.extractfile(member).read()
checked=set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);name=name.removeprefix('./')
    assert name not in checked and hashlib.sha256(files[name]).hexdigest()==digest
    checked.add(name)
assert checked==files.keys()-{'SHA256SUMS'}
assert files['exit-status.txt']==b'0\n' and files['result.txt']==b'TRACE_CONNECTIVITY_CAPTURE_PASS\n'
assert files['debug-mask.txt']==b'0\n'
assert set(re.findall(r'overrun:\s*(\d+)',files['trace-stats.txt'].decode()))=={'0'}
records=[]
for line in files['trace.txt'].decode().splitlines():
    match=re.match(r'^\s*\S+-(\d+)\s+\[\d+\]\s+\S+\s+([\d.]+): (\w+): (.*)',line)
    if match: records.append(dict(pid=int(match[1]),time=float(match[2]),event=match[3],message=match[4]))
keys=[]
for i,record in enumerate(records):
    if record['event']!='drv_set_key': continue
    match=re.search(r'cmd: (\d+).*flags=(0x[0-9a-f]+), keyidx=(\d+)',record['message'])
    assert match
    key=dict(cmd=int(match[1]),flags=int(match[2],16),keyidx=int(match[3]),time=record['time'],pid=record['pid'])
    later=records[i+1:]
    returned=next(x for x in later if x['event']=='drv_return_int' and x['pid']==record['pid'])
    key['return']=int(returned['message'].rsplit(' - ',1)[1])
    key['duration_ms']=round(1000*(returned['time']-key['time']),3)
    acknowledgments=[x for x in later if x['time']<=returned['time'] and x['event']=='ath10k_log_dbg' and 'sec ind ' in x['message']]
    key['security_indications_before_return']=len(acknowledgments)
    keys.append(key)
pairwise=[x for x in keys if x['cmd']==1 and x['flags']&8]
assert len(pairwise)==3 and all(x['return']==-110 and x['duration_ms']>=3000 and x['security_indications_before_return']==0 for x in pairwise)
installs=[x for x in keys if x['cmd']==0]
assert len(installs)==8 and all(x['return']==0 and x['security_indications_before_return']==1 for x in installs)
samples=files['coexistence-samples.txt'].decode().splitlines()
assert len(samples)==45 and [int(re.search(r'sample=(\d+)',line)[1]) for line in samples]==list(range(1,46))
assert all('MPSS=running taint=0' in line for line in samples)
reasons=re.findall(r'CTRL-EVENT-DISCONNECTED[^\n]*reason=(\d+)',files['wpa-after.log'].decode())
assert reasons.count('7')==1 and reasons.count('3')==1
scan=files['bt-scan.txt'].decode()
assert 'command=0x0024 status=0x00' in scan and scan.count('command=0x0023 status=0x00')>=1
scan_count=len(set(re.findall(r'address=([0-9A-F:]+) type=(\d+)',scan)))
payload=bytes.fromhex(re.search(r'command=0x0004 status=0x00 payload=([0-9a-f]+)',files['bt-final-info.txt'].decode())[1])
assert len(payload)==280 and int.from_bytes(payload[13:17],'little')&0x1b==0
before=files['dmesg-before.txt'].decode();after=files['dmesg-after.txt'].decode()
assert before.count('frame done timeout')==after.count('frame done timeout')==1
errors=re.findall(r'Frame reassembly failed \(-84\) phase=(\d+) baud=(\d+) chunk=(\d+) partial=(\d+) first=([0-9a-f]{2})',after)
assert len(errors)==3 and all(x==('2','115200','1','0','00') for x in errors)
assert files['state.txt'].decode().splitlines()[-2:]==['0','running']
for phase,freq in [('initial',2462),('reconnect',2462),('five-ghz',5180)]:
    status=files[phase+'-status.txt'].decode()
    assert 'wpa_state=COMPLETED\n' in status and f'freq={freq}\n' in status
report=dict(trace_evidence_audit_pass=True,verified_private_files=len(checked),
    archive_sha256=hashlib.sha256((out/'trace-connectivity.tar').read_bytes()).hexdigest(),
    trace_overruns=0,raw_wmi_and_key_dump_events_enabled=False,ath10k_debug_mask=0,
    pairwise_delete_waits_ms=[x['duration_ms'] for x in pairwise],
    pairwise_delete_security_indications=0,successful_key_installations=len(installs),
    key_install_return_latency_ms=[x['duration_ms'] for x in installs],
    unforced_reason7_disconnects=1,controlled_reason3_disconnects=1,
    snapshot_samples=45,non_completed_snapshot_samples=sum('WPA=COMPLETED' not in x for x in samples),
    uninterrupted_scan_coexistence_pass=False,snapshots_missed_transient_disconnect=True,
    scan_window_seconds=100,scan_address_type_records=scan_count,
    discovery_starts=scan.count('command=0x0023 status=0x00'),final_bt_powered=False,
    display_timeouts_before_trace=1,new_display_timeouts_during_trace=0,
    bt_frame_errors=3,bt_error_phase='power_on_pulse',single_zero_byte_observed=True,
    wifi_unforced_disconnect_root_cause_resolved=False,key_wait_behavior_unchanged=True,goal_complete=False)
(out/'trace-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
