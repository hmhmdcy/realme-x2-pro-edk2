"""Check the user's changed orientation using paired RAM stats and two exposures."""
from pathlib import Path
import ast
import hashlib
import json
import shutil
import subprocess

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel240')
SDK = Path('/home/cy122/x2pro-linux/libcamera214-root')
source = (R.parent / 'kernel239/paired-probe.cpp').read_text()
source = source.replace('>= 12', '>= 24').replace('< 12;', '< 24;').replace('== 12 ||', '== 24 ||')
source = source.replace('static void manual(ControlList &controls)', 'static void manual(ControlList &controls, unsigned int index = 0)')
source = source.replace('controls.set(controls::ExposureTime, 2000);', 'controls.set(controls::ExposureTime, index < 12 ? 2000 : 32000);')
source = source.replace('indices_[request] = nextQueued_++; manual(request->controls());', 'indices_[request] = nextQueued_++; manual(request->controls(), indices_[request]);')
source = source.replace('std::abs(*exposure - 2000) <= 20 &&', '(std::abs(*exposure - 2000) <= 20 || std::abs(*exposure - 32000) <= 40) &&')
source = source.replace('Measurement rawStats, rgbStats;', 'Measurement rawStats, rgbStats;\n        std::array<Measurement, 4> bayer;\n        std::array<Measurement, 3> channels;')
source = source.replace('for (unsigned int x = 0; x < raw_.size.width; ++x) rawStats.add(raw10(line, x));', '''for (unsigned int x = 0; x < raw_.size.width; ++x) {
                const auto value = raw10(line, x);
                rawStats.add(value); bayer[(y % 2) * 2 + x % 2].add(value);
            }''')
source = source.replace('for (unsigned int x = 0; x < rgb_.size.width * 3; ++x) rgbStats.add(line[x]);', '''for (unsigned int x = 0; x < rgb_.size.width * 3; ++x) {
                rgbStats.add(line[x]); channels[x % 3].add(line[x]);
            }''')
needle = '<< ",\\\"raw\\\":" << rawStats.json(true) << ",\\\"rgb\\\":" << rgbStats.json(false) << \'}\';'
assert source.count(needle) == 1
source = source.replace(needle, '''<< ",\\\"raw\\\":" << rawStats.json(true) << ",\\\"rgb\\\":" << rgbStats.json(false)
            << ",\\\"bayer\\\":[";
        for (unsigned int i = 0; i < bayer.size(); ++i) { if (i) out << ','; out << bayer[i].json(false); }
        out << "],\\\"rgb_channels\\\":[";
        for (unsigned int i = 0; i < channels.size(); ++i) { if (i) out << ','; out << channels[i].json(false); }
        out << "]}";''')
source = source.replace('twelve complete same-request RAW/RGB pairs', 'twenty-four complete same-request RAW/RGB pairs')
(R / 'upright-paired-probe.cpp').write_text(source)
shutil.copyfile(R / 'upright-paired-probe.cpp', SDK / 'private/upright-paired-probe240.cpp')
prefix = '/candidate239-r15'
command = ['chroot', str(SDK), '/usr/bin/g++', '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread',
    '-I'+prefix+'/usr/include/libcamera', '/private/upright-paired-probe240.cpp', '-L'+prefix+'/usr/lib',
    '-Wl,-rpath-link,'+prefix+'/usr/lib', '-lcamera', '-lcamera-base', '-o', '/private/upright-paired-probe240']
result = subprocess.run(command, capture_output=True, timeout=180)
(P / 'upright-paired-build-private.log').write_bytes(result.stdout + result.stderr)
assert result.returncode == 0, 'inspect retained compiler diagnostics'
test = subprocess.run(['chroot', str(SDK), '/usr/bin/env', 'LD_LIBRARY_PATH='+prefix+'/usr/lib',
    '/private/upright-paired-probe240', '--self-test'], capture_output=True, timeout=15)
(P / 'upright-paired-selftest-private.log').write_bytes(test.stdout + test.stderr)
assert test.returncode == 0 and json.loads(test.stdout)['raw10_known_wire_vector_passed']
binary = P / 'upright-paired-probe240'
shutil.copyfile(SDK / 'private/upright-paired-probe240', binary)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = dict(stage=240, source_sha256=sha(R / 'upright-paired-probe.cpp'), binary_sha256=sha(binary),
    binary_bytes=binary.stat().st_size, werror_clean=True, raw10_wire_selftest_passed=True,
    paired_requests=24, exposure_phases_requested_us=[2000,32000], manual_gain=1,
    no_scene_images_saved=True, user_reported_phone_upright=True)
(R / 'upright-build-validation.json').write_text(json.dumps(report, indent=2)+'\n')
native = (R.parent / 'kernel239/native-paired.py').read_text()
native = native.replace('k239-paired-r14', 'k240-upright-paired-r15').replace('stage=239','stage=240')
native = native.replace(" assert json.loads((root/'k238-candidate-permissions-fix/summary.json').read_text())['uid10000_cpu_config_read_verified']", " assert json.loads((root/'k240-baseline/summary.json').read_text())['installed_r15_r10']")
a = native.index(" prefix=Path('/run/samurai-camera238-r14')")
b = native.index('\n dims=', a)
native = native[:a] + " env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR='/run/user/10000',LIBCAMERA_LOG_LEVELS='*:INFO,SimplePipeline:DEBUG,Debayer:DEBUG,IPASoftBL:DEBUG')" + native[b:]
native = native.replace('/run/samurai-camera238-probes/paired-probe239', '/run/samurai-camera240-probes/upright-paired-probe240')
native = native.replace('k239_paired_controls','k240_upright_controls').replace('len(frames)==12','len(frames)==24')
native = native.replace("if '/run/samurai-camera238-r14/' in line", "if '/usr/lib/libcamera' in line")
native = native.replace("'/run/samurai-camera238-r14/usr/lib/'+name", "'/usr/lib/'+name")
native = native.replace('paired_same_request=True,', 'paired_same_request=True,user_reported_phone_upright=True,default_system_r15_no_candidate_overrides=True,')
native = native.replace('fixed_exposure_gain=True,', 'exposure_requested_phases_us=[2000,32000],fixed_gain=1,')
ast.parse(native)
(R / 'native-upright.py').write_text(native)
print(json.dumps(report))
