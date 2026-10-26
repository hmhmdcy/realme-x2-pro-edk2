#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import re
import tarfile

private = Path('/mnt/e/edk2-samurai-out/kernel131')
public = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel131')

def verified_archive(name):
    path = private / name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == Path(str(path) + '.sha256').read_text().split()[0]
    with tarfile.open(path) as archive:
        members = {m.name.removeprefix('./'): archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
    manifest = members['SHA256SUMS'].decode().splitlines()
    assert len(manifest) == len(members) - 1
    for entry in manifest:
        expected, filename = entry.split('  ', 1)
        assert hashlib.sha256(members[filename.removeprefix('./')]).hexdigest() == expected
    return members, hashlib.sha256(path.read_bytes()).hexdigest()

data, archive_sha = verified_archive('k131-native-fbo-comparison-private.tar.gz')
build, build_sha = verified_archive('k131-native-build-private.tar.gz')
assert data['run-exit.txt'].strip() == b'2'
assert data['taint-final.txt'].strip() == b'0'
result = {'kernel': 129, 'mesa': '26.2.4', 'renderer': 'FD640',
          'scene': 'build:use-vbo=true', 'archive_sha256': archive_sha,
          'build_archive_sha256': build_sha, 'archive_verified_members': len(data) - 1,
          'build_verified_members': len(build) - 1, 'variants': {}}
fault_pattern = re.compile(r'gpu.*fault|FAULT.*gpu|CCU.*TRANSLATION|CP.*FAULT', re.I)
for variant, size, validation in [('control', '1080x2259', 'Failure'), ('fixed', '800x600', 'Success')]:
    prefix = variant + '/'
    log = data[prefix + 'validation-private.txt'].decode()
    assert 'Actual FBO Size: ' + size + '; Canvas Size: ' + size in log
    assert 'GL_RENDERER:    FD640' in log
    assert 'OpenGL ES 3.2 Mesa 26.2.4' in log
    assert log.count('Validation: ' + validation) == 1
    assert 'Surface Size:   1080x2259 windowed' in log
    assert data[prefix + 'exit.txt'].strip() == b'0'
    assert data[prefix + 'taints.txt'].decode().split() == ['0'] * 7
    assert data[prefix + 'phosh-before.txt'] == data[prefix + 'phosh-after.txt']
    assert data[prefix + 'phoc-before.txt'] == data[prefix + 'phoc-after.txt']
    before = data[prefix + 'dmesg-before.txt'].decode().splitlines()
    after = data[prefix + 'dmesg-delayed.txt'].decode().splitlines()
    assert after[:len(before)] == before
    new_faults = [line for line in after[len(before):] if fault_pattern.search(line)]
    samples = [float(line.split()[1]) for line in data[prefix + 'samples.txt'].decode().splitlines()]
    assert len(samples) == 7 and samples[-1] - samples[0] >= 30
    exit_uptime = float(data[prefix + 'uptime-exit.txt'].split()[0])
    fault_events = [line for line in new_faults if '*** gpu fault:' in line]
    fault_delays = [round(float(re.search(r'\[\s*([0-9.]+)\]', line).group(1)) - exit_uptime, 3) for line in fault_events]
    result['variants'][variant] = {'actual_fbo': size, 'pixel_validation': validation.upper(),
                                   'process_exit': 0, 'new_gpu_fault_lines': len(new_faults),
                                   'new_gpu_translation_events': len(fault_events),
                                   'fault_seconds_after_exit': fault_delays,
                                   'observation_seconds': round(samples[-1] - samples[0], 3),
                                   'desktop_pids_unchanged': True}
    assert len(new_faults) == (0 if variant == 'control' else 3)
    assert len(fault_events) == (0 if variant == 'control' else 2)
    if variant == 'fixed':
        assert all('CCU' in line and 'READ' in line and 'TRANSLATION' in line for line in fault_events)
        assert all(delay > 0 for delay in fault_delays)
        iovas = [re.search(r'iova=([^ ]+)', line).group(1) for line in fault_events]
        result['variants'][variant]['repeated_fault_iova'] = iovas[0] == iovas[1]
    dynamic = data[variant + '-dynamic.txt'].decode()
    assert 'RUNPATH' not in dynamic and 'RPATH' not in dynamic
assert 'Expected: 0xffa7a7a7 Actual: 0xffa5a5a5' in data['control/validation-private.txt'].decode()
control = build['canvas-control.cpp'].decode()
fixed = build['canvas-fixed.cpp'].decode()
anchor = '    width_ = cur_properties.width;\n    height_ = cur_properties.height;'
replacement = '    const bool fixed_validation_size = offscreen_ && Options::validate && width > 0 && height > 0;\n    width_ = fixed_validation_size ? width : cur_properties.width;\n    height_ = fixed_validation_size ? height : cur_properties.height;'
assert control.count(anchor) == 1 and control.replace(anchor, replacement) == fixed
for receipt in json.loads(build['build-receipts.json']):
    body = build['glmark2-es2-wayland-' + receipt['variant']]
    assert len(body) == receipt['bytes'] and hashlib.sha256(body).hexdigest() == receipt['sha256']
for name in ['package-db-final-check.txt', 'nv-check.txt', 'source-check.txt', 'vendor-check.txt']:
    assert all(line.endswith(': OK') for line in data[name].decode().splitlines())
cores = [(name, body) for name, body in data.items() if name.endswith('-private.data')]
assert len(cores) == 1
core_name, core = cores[0]
core_dir = private / 'gpu-coredump'
core_dir.mkdir(mode=0o700, exist_ok=True)
core_path = core_dir / core_name
if core_path.exists():
    assert core_path.read_bytes() == core
else:
    core_path.write_bytes(core)
result.update(core_name=core_name, core_bytes=len(core), core_sha256=hashlib.sha256(core).hexdigest(),
              fbo_size_fault_proven=True, validation_threshold_unchanged=True,
              driver_fault_unresolved=True, full_gpu_acceptance=False,
              package_nv_sources_preserved=True)
(public / 'fbo-comparison-validation.json').write_text(json.dumps(result, indent=2) + '\n')
(public / 'fbo-size-only.patch').write_bytes(build['fbo-size-only.patch'])
(public / 'native-build-receipts.json').write_bytes(build['build-receipts.json'])
print(json.dumps(result))
