"""Build standard applications for joint-latch and AE tests; do not contact a phone."""
from pathlib import Path
import hashlib, json, shutil, subprocess
import host
HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'kernel302'
SDK = Path('/home/cy122/x2pro-linux/libcamera214-root')
stage = SDK / 'private/camss303-runtime'
stage.mkdir(exist_ok=True)
base = (OLD / 'pipeline-smoke.cpp').read_text()
start = base.index(' int exposure = sequence == 24')
end = base.index(' if (exposure) request', start)
joint = base[:start] + ''' const bool change = sequence >= 24 && sequence <= 216 && sequence % 24 == 0;
 int exposure = change ? (sequence / 24 % 2 ? 10000 : 20000) : 0;
 float gain = change ? (sequence / 24 % 2 ? 4.0f : 2.0f) : 0;
''' + base[end:]
joint = joint.replace('controls.set(controls::ExposureTime, int32_t(5000))', 'controls.set(controls::ExposureTime, int32_t(20000))')
auto = base
start = auto.index(' int exposure = sequence == 24')
end = auto.index('\n}\n\nclass Capture', start)
auto = auto[:start] + ' (void)sequence; (void)epoch;' + auto[end:]
auto = auto.replace('ExposureTimeModeManual', 'ExposureTimeModeAuto').replace('AnalogueGainModeManual', 'AnalogueGainModeAuto')
auto = auto.replace('controls.set(controls::ExposureTime, int32_t(5000))', 'controls.set(controls::ExposureTime, int32_t(epoch ? 30000 : 5000))')
auto = auto.replace('controls.set(controls::AnalogueGain, 2.0f)', 'controls.set(controls::AnalogueGain, epoch ? 16.0f : 2.0f)')
results = {}
for kind, source in [('joint', joint), ('ae', auto)]:
    (HERE / f'{kind}-smoke.cpp').write_text(source)
    shutil.copyfile(HERE / f'{kind}-smoke.cpp', stage / f'{kind}.cpp')
    q = subprocess.run(['chroot', str(SDK), '/usr/bin/g++', '-std=c++20', '-O0', '-Wall', '-Wextra', '-Werror',
     '-I/candidate278-r24/usr/include/libcamera', '/private/camss303-runtime/' + kind + '.cpp',
     '-L/candidate278-r24/usr/lib', '-Wl,-rpath-link,/candidate278-r24/usr/lib', '-lcamera', '-lcamera-base', '-pthread',
     '-o', '/private/camss303-runtime/' + kind], capture_output=True, timeout=180)
    (host.PRIVATE / f'{kind}-application-compile-private.log').write_bytes(q.stdout + q.stderr)
    assert q.returncode == 0, q.stderr.decode()
    shutil.copyfile(stage / kind, host.PRIVATE / f'{kind}-smoke-aarch64-private')
    results[kind] = dict(werror_compile=True, source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                         binary_sha256=hashlib.sha256((stage / kind).read_bytes()).hexdigest(),
                         hardware_tested=False)
fixture = host.PRIVATE.parent / 'kernel300/pipeline-fixture-aarch64-private'
assert hashlib.sha256(fixture.read_bytes()).hexdigest() == '5f5fcbf0300a539327edf699272ffc383a44a3d34bb55ad17ef9ea3ed71b3319'
shutil.copyfile(fixture, host.PRIVATE / 'pipeline-fixture-aarch64-private')
(HERE / 'runtime-tools-validation.json').write_text(json.dumps(dict(stage=303, applications=results, fixture_hash_verified=True), indent=2) + '\n')
print(json.dumps(results, indent=2))
