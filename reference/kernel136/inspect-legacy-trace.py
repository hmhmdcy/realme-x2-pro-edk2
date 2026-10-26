from pathlib import Path
import hashlib
import json
import re
import tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel136')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel136')
with tarfile.open(out / 'legacy-vm-trace-private.tar.gz') as archive:
    d = {m.name.removeprefix('./'): archive.extractfile(m).read()
         for m in archive if m.isfile()}
for line in d['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ', 1)
    assert hashlib.sha256(d[name.removeprefix('./')]).hexdigest() == digest
with tarfile.open(out / 'first-runtime-private.tar.gz') as archive:
    assert d['boot-id-private.txt'] == archive.extractfile('./boot-id-private.txt').read()
run = json.loads(d['run-result.json'])
assert run['test_exit'] == 0 and run['error'] is None
assert run['parameter_restored'] and run['trace_removed']
assert d['taint-final.txt'].strip() == b'512'
assert d['vm-log-final.txt'].strip() == b'0'
assert d['desktop-pids-before.json'] == d['desktop-pids-final.json']
assert b'Actual FBO Size: 800x600; Canvas Size: 800x600' in d['pixel-validation-private.txt']
assert b'Validation: Success' in d['pixel-validation-private.txt']
assert b'FD640' in d['pixel-validation-private.txt']
for name, count in [('nv-check.txt',6), ('source-check.txt',4), ('vendor-check.txt',1), ('package-db-check.txt',2)]:
    assert d[name].count(b': OK') == count and b'FAILED' not in d[name]
t = d['submission-trace-private.txt'].decode()
maps = []
switches = []
for line in t.splitlines():
    m = re.search(r'([0-9.]+): msm_gpu_vm_update: pid=(\d+) ttbr=([0-9a-f]+) managed=(\d) op=(\S+) iova=([0-9a-f]+) range=([0-9a-f]+) queue=(-?\d+) ret=(-?\d+)', line)
    if m:
        maps.append(dict(time=float(m[1]), pid=int(m[2]), ttbr=int(m[3],16), managed=bool(int(m[4])),
            op=m[5], start=int(m[6],16), size=int(m[7],16), queue=int(m[8]), ret=int(m[9])))
    m = re.search(r'([0-9.]+): msm_gpu_vm_switch_enqueue: pid=(\d+) ring=(\d+) seqno=(\d+) old_ctx=(\d+) new_ctx=(\d+) ttbr=([0-9a-f]+)', line)
    if m:
        switches.append(dict(time=float(m[1]),pid=int(m[2]),ring=int(m[3]),seq=int(m[4]),
            old_ctx=int(m[5]),new_ctx=int(m[6]),ttbr=int(m[7],16)))
assert maps and switches
before = d['dmesg-before-private.txt'].decode()
after = d['dmesg-final-private.txt'].decode()
cores = []
private_cores = []
for name, raw in d.items():
    if not name.endswith('-private.data'):
        continue
    (out / name).write_bytes(raw)
    text = raw.decode(errors='replace')
    info = re.search(r'^fault-info:\n(.*?)(?=^[a-z]|\Z)', text,re.S|re.M)
    record = dict(name=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                  comm=re.search(r'^comm: (.*)$',text,re.M)[1])
    detail = dict(record)
    if info:
        addr = int(re.search(r'iova=(?:0x)?([0-9a-fA-F]+)',info[1])[1],16)
        record.update({key:re.search(key + r'=(\S+)',info[1])[1] for key in ['dir','type','source']})
        detail['fault_iova'] = addr
        contains = [m for m in maps if m['start'] <= addr < m['start'] + m['size']]
        record['all_vm_operations_covering_fault_address'] = len(contains)
        detail['all_matching_operations'] = contains
        record['matching_operation_types'] = sorted(set(m['op'] for m in contains))
        record['matching_pid_count'] = len(set(m['pid'] for m in contains))
    private_cores.append(detail)
    cores.append(record)
stats = json.loads(d['trace-stats.json'])
report = dict(stage=136,kernel_build=136,software_generation=132,
    diagnostic_only_preexisting_audio_taint=512, pixel_scene_pass=True,actual_fbo=[800,600],
    vm_map_events=sum(m['op']=='map' for m in maps),
    vm_unmap_events=sum(m['op']!='map' for m in maps),
    vm_failed_map_events=sum(m['op']=='map' and m['ret'] != 0 for m in maps),
    managed_vm_mapping_events=sum(m['managed'] for m in maps),
    vm_switch_enqueue_events=len(switches),
    submit_flush_events=t.count('msm_gpu_submit_flush:'),
    submit_retired_events=t.count('msm_gpu_submit_retired:'),
    trace_overruns=sum(int(re.search(r'^overrun:\s*(\d+)',s,re.M)[1]) for s in stats.values()),
    gpu_faults=after.count('gpu fault:'),cores=cores,
    desktop_pids_preserved_in_window=True,elapsed_seconds=run['elapsed_seconds'],
    output_kept_enabled=True,vm_log_parameter_kept_zero=True,new_trace_instance_removed=True,
    source_and_package_hashes_pass=True,root_cause_proven=False,gpu_fix_accepted=False,goal_complete=False)
for name, pattern in [('dpu_timeouts',r'frame done timeout'),('dsi_errors',r'dsi_err_worker'),
                      ('kernel_warns',r'WARNING:'),('codec_enospc',r'Failed to read.*-28')]:
    report[name] = dict(before=len(re.findall(pattern,before)),after=len(re.findall(pattern,after)))
samples = json.loads(d['power-samples-private.json'])
report['charging'] = dict(sample_count=len(samples),online_samples=sum(s['properties']['online'].get('value','').strip()=='1' for s in samples),
    voltage_samples=sum('value' in s['properties']['voltage_now'] for s in samples),
    current_samples=sum('value' in s['properties']['current_now'] for s in samples),charging_control_accepted=False)
(out / 'legacy-vm-operations-private.json').write_text(json.dumps(dict(maps=maps,switches=switches,cores=private_cores),indent=2))
for name in ['submission-trace-private.txt','dmesg-final-private.txt','drm-final-private.txt','ioctl-private.txt']:
    (out / name).write_bytes(d[name])
(ref / 'legacy-vm-trace-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
