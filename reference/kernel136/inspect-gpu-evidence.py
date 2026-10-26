from pathlib import Path
import hashlib
import json
import re
import tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel136')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel136')

def load(name):
    with tarfile.open(out / name) as archive:
        data = {m.name.removeprefix('./'): archive.extractfile(m).read()
                for m in archive if m.isfile()}
    for line in data['SHA256SUMS'].decode().splitlines():
        digest, path = line.split('  ', 1)
        assert hashlib.sha256(data[path.removeprefix('./')]).hexdigest() == digest
    return data

base = load('current132-private.tar.gz')
data = load('gpu-evidence-private.tar.gz')
assert base['boot-id-private.txt'] == data['boot-id-private.txt']
for name, count in [('nv-check.txt', 6), ('source-check.txt', 4), ('vendor-check.txt', 1)]:
    assert data[name].count(b': OK') == count and b'FAILED' not in data[name]
    assert base[name].count(b': OK') == count and b'FAILED' not in base[name]
assert base['module-check.txt'].count(b': OK') >= 770
assert base['gui-check.txt'].count(b': OK') == 3
assert data['package-db-check.txt'].count(b': OK') == 2
assert data['desktop-pids-before.json'] == data['desktop-pids-final.json']
assert data['taint-final.txt'].strip() == b'0'
assert data['vm-log-final.txt'].strip() == b'0'
run = json.loads(data['run-result.json'])
assert run['error'] is None and run['test_exit'] == 0
assert run['parameter_restored'] and run['trace_removed']
pixel = data['pixel-validation-private.txt'].decode()
assert 'Actual FBO Size: 800x600; Canvas Size: 800x600' in pixel
assert 'Validation: Success' in pixel and 'FD640' in pixel
before = data['dmesg-before-private.txt'].decode()
after = data['dmesg-final-private.txt'].decode()
for stem in ['dmesg', 'ioctl', 'submission-trace', 'gpu-before']:
    name = stem + '-private.txt'
    if name in data:
        (out / name).write_bytes(data[name])
fault_pattern = re.compile(r'^.*gpu fault:.*$', re.M)
faults = fault_pattern.findall(after)
report = dict(stage=136, actual_kernel=132, new_current_boot_revalidated=True,
              gpu_pixel_scene='build:use-vbo=true', actual_fbo=[800, 600],
              gpu_renderer='FD640', pixel_validation_pass=True, test_exit=run['test_exit'],
              delayed_observation_samples=8, gpu_fault_events=len(faults),
              vm_history_parameter_scoped_to_new_probe_vms=True,
              vm_history_parameter_restored=True, no_shader_cache_flush_mode_changed=True,
              diagnostic_trace_instance_removed=True, desktop_pids_preserved=True, taint=0,
              source_modules_and_partitions_preserved=True, goal_complete=False)
cores = []
for name, raw in data.items():
    if name.endswith('-private.data'):
        (out / name).write_bytes(raw)
        t = raw.decode(errors='replace')
        vm_section = re.search(r'^vm-log:\n(.*?)(?=^[a-z]|\Z)', t, re.S | re.M)
        fault = re.search(r'^fault-info:\n(.*?)(?=^[a-z]|\Z)', t, re.S | re.M)
        bos_section = re.search(r'^bos:\n(.*?)(?=^[a-z]|\Z)', t, re.S | re.M)
        core = dict(name=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                    vm_history_present=vm_section is not None,
                    comm=re.search(r'^comm: (.*)$', t, re.M)[1])
        if fault:
            addr = int(re.search(r'iova=(?:0x)?([0-9a-fA-F]+)', fault[1])[1], 16)
            core['fault_direction'] = re.search(r'dir=(\S+)', fault[1])[1]
            core['fault_type'] = re.search(r'type=(\S+)', fault[1])[1]
            core['fault_source'] = re.search(r'source=(\S+)', fault[1])[1]
            if vm_section:
                entries = []
                for line in vm_section[1].splitlines():
                    m = re.search(r'(?:op:| -)\s*(\w+).*?(?:iova:|0x)\s*(?:0x)?([0-9a-fA-F]+)', line)
                    if m:
                        entries.append(line)
                core['vm_history_entry_lines'] = len(vm_section[1].splitlines())
                core['fault_matches_vm_history_text'] = format(addr, 'x') in vm_section[1].lower()
            if bos_section:
                bos = [(int(m[1], 16), int(m[2])) for m in re.finditer(r'  - iova: ((?:0x)?[0-9a-fA-F]+)\n    size: ([0-9]+)', bos_section[1])]
                core['listed_bo_count'] = len(bos)
                core['fault_within_listed_bo'] = any(start <= addr < start + size for start, size in bos)
        cores.append(core)
report['cores'] = cores
ioctl = data['ioctl-private.txt'].decode()
report['vm_bind_ioctl_seen'] = 'DRM_IOCTL_MSM_VM_BIND' in ioctl or '0xc0286454' in ioctl.lower()
report['ioctl_calls'] = ioctl.count('ioctl(')
stats = json.loads(data['trace-stats.json'])
report['trace_overruns'] = sum(int(re.search(r'^overrun:\s*(\d+)', text, re.M)[1]) for text in stats.values())
trace = data['submission-trace-private.txt'].decode()
report['submit_flush_events'] = trace.count('msm_gpu_submit_flush:')
report['submit_retired_events'] = trace.count('msm_gpu_submit_retired:')
report['gpu_overall_accepted'] = False
report['root_cause_proven'] = False
samples = json.loads(data['power-samples-private.json'])
report['charging'] = dict(standard_events_persisted=len(samples),
    online_one_samples=sum(s['properties']['online'].get('value', '').strip() == '1' for s in samples),
    voltage_samples=sum('value' in s['properties']['voltage_now'] for s in samples),
    current_samples=sum('value' in s['properties']['current_now'] for s in samples),
    charging_control_accepted=False)
for stem, pattern in [('dpu_timeouts', r'frame done timeout'), ('dsi_errors', r'dsi_err_worker'),
                       ('warns', r'WARNING:'), ('codec_enospc', r'Failed to read.*-28')]:
    report[stem] = dict(before=len(re.findall(pattern, before)), after=len(re.findall(pattern, after)))
(ref / 'gpu-evidence-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
