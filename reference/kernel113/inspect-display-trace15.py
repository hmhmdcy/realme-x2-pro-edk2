from pathlib import Path
import collections, hashlib, json, re, tarfile

out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
path=out/'display-trace15.tar'
with tarfile.open(path) as archive:
    raw={}
    for entry in archive:
        if not entry.isfile():
            assert not entry.issym() and not entry.islnk()
            continue
        name=entry.name.removeprefix('./')
        assert not Path(name).is_absolute() and '..' not in Path(name).parts and name not in raw
        raw[name]=archive.extractfile(entry).read()
count=0
for line in raw['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1)
    assert hashlib.sha256(raw[name.removeprefix('./')]).hexdigest()==digest
    count+=1
assert b'#113 SMP PREEMPT' in raw['uname.txt']
assert raw['slpi.txt'].strip()==b'offline' and raw['power.txt'].strip()==b'vdd=0 vddio=0'
assert raw['trace-exit.txt'].strip()==raw['snapshot-exit.txt'].strip()==b'0'
report=dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),nested_files_verified=count,
            boot_checkpoint='reboot-audio-clean-15',taint=int(raw['state.txt'].splitlines()[-1]),
            tracing_on=raw['tracing_on.txt'].decode().strip(),trace_clock=raw['trace_clock.txt'].decode().strip(),
            buffer_size_kb=int(raw['buffer_size_kb.txt']),watchdog_enabled=raw['watchdog-enable.txt'].decode().strip(),
            timeout_trigger=raw['timeout-trigger.txt'].decode().strip(),
            traces_and_snapshot_read_only=True,raw_logs_private=True)
for kind in ('trace','snapshot'):
    text=raw[kind+'.txt'].decode(errors='strict')
    events=re.findall(r'\s(\d+\.\d+): (\w+): (.*)',text)
    counts=collections.Counter(name for _,name,_ in events)
    selected=[(stamp,name,body) for stamp,name,body in events if name=='dpu_enc_frame_done_timeout' or
              (name=='dpu_enc_frame_watchdog' and 'action=expire' in body)]
    windows=[]
    for i,(_,name,_) in enumerate(events):
        if name=='dpu_enc_frame_done_timeout':
            windows.append([' '.join(row) for row in events[max(0,i-35):i+8]])
    (out/f'display-{kind}15-timeout-windows-private.json').write_text(json.dumps(windows,indent=2)+'\n')
    report[kind]=dict(bytes=len(raw[kind+'.txt']),sha256=hashlib.sha256(raw[kind+'.txt']).hexdigest(),
                      events=len(events),event_counts=dict(counts),
                      first_timestamp=events[0][0] if events else None,last_timestamp=events[-1][0] if events else None,
                      timeout_watchdog_decisions=[' '.join(row) for row in selected])
report['dpu_frame_done_timeouts']=raw['dmesg.txt'].count(b'frame done timeout')
report['gpu_faults']=raw['dmesg.txt'].count(b'*** gpu fault')
report['permanent_display_fix_accepted']=False
report['goal_complete']=False
(ref/'display-trace15-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
