"""Build bounded same-request RAW/RGB manual-response and AE observations."""
from pathlib import Path
import hashlib, json, shutil, subprocess
import host

R = Path(__file__).resolve().parent
old = R.parent / 'kernel270/telephoto-paired-probe.cpp'
proof = json.loads(old.with_name('paired-probe-build-validation.json').read_text())
text = old.read_text()
assert hashlib.sha256(text.encode()).hexdigest() == proof['source_sha256']
plans = [(2000,1), (8000,1), (32000,1), (32000,2), (32000,4), (32000,8), (32000,16), (32000,1)]
insertion = '''
static bool automaticMode = false;
static unsigned int requestedFrames = 96;
static const std::array<std::pair<int, float>, 8> controlPlan = {{{2000,1}, {8000,1}, {32000,1}, {32000,2}, {32000,4}, {32000,8}, {32000,16}, {32000,1}}};
'''
text = text.replace('using namespace libcamera;', 'using namespace libcamera;\n' + insertion)
start = text.index('        controls.set(controls::AeEnable, false);')
end = text.index('\n    }\n    int queue(', start)
text = text[:start] + '''        controls.set(controls::AeEnable, automaticMode);
        controls.set(controls::ExposureTimeMode, automaticMode ? controls::ExposureTimeModeAuto : controls::ExposureTimeModeManual);
        controls.set(controls::AnalogueGainMode, automaticMode ? controls::AnalogueGainModeAuto : controls::AnalogueGainModeManual);
        if (!automaticMode) {
            const auto &setting = controlPlan.at(index / 12);
            controls.set(controls::ExposureTime, setting.first);
            controls.set(controls::AnalogueGain, setting.second);
        }''' + text[end:]
text = text.replace('nextQueued_ >= 24', 'nextQueued_ >= requestedFrames').replace('frames_.size() >= 24', 'frames_.size() >= requestedFrames')
text = text.replace('frames_.size() < 24', 'frames_.size() < requestedFrames').replace('frames_.size() == 24', 'frames_.size() == requestedFrames')
start = text.index('        require((std::abs(*exposure - 2000)')
end = text.index('\n        ReadMapping rawMap', start)
text = text[:start] + '''        require(*exposure > 0 && *gain >= 1.0f && *gain <= 16.0f, "bounded physical controls");
        require(*exposureMode == (automaticMode ? controls::ExposureTimeModeAuto : controls::ExposureTimeModeManual) &&
                *gainMode == (automaticMode ? controls::AnalogueGainModeAuto : controls::AnalogueGainModeManual),
                "captured control modes");
        if (!automaticMode && index % 12 >= 6) {
            const auto &expected = controlPlan.at(index / 12);
            require(std::abs(*exposure - expected.first) <= 40 && std::abs(*gain - expected.second) < 0.03f,
                    "stable captured metadata matches manual phase");
        }''' + text[end:]
text = text.replace('std::chrono::seconds(45)', 'std::chrono::seconds(100)')
text = text.replace('std::string(argv[8]) != "1") return 2;', '(std::string(argv[8]) != "manual" && std::string(argv[8]) != "auto")) return 2;\n    automaticMode = std::string(argv[8]) == "auto";\n    requestedFrames = automaticMode ? 180 : 96;')
text = text.replace('twenty-four complete same-request RAW/RGB pairs', 'all planned same-request RAW/RGB pairs')
assert 'nextQueued_ >= 24' not in text and 'std::string(argv[8]) != "manual"' in text
source = R / 'telephoto-control-probe.cpp'
source.write_text(text)
sdk = Path('/home/cy122/x2pro-linux/libcamera214-root')
name = 'telephoto-control-probe271'
assert not (sdk / 'private' / name).exists()
shutil.copyfile(source, sdk / 'private' / (name + '.cpp'))
prefix = '/candidate239-r15'
q = subprocess.run(['chroot', str(sdk), '/usr/bin/g++', '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread',
                    '-I'+prefix+'/usr/include/libcamera', '/private/'+name+'.cpp', '-L'+prefix+'/usr/lib',
                    '-Wl,-rpath-link,'+prefix+'/usr/lib', '-lcamera', '-lcamera-base', '-o', '/private/'+name],
                   capture_output=True, timeout=150)
(host.PRIVATE / 'control-probe-build-private.log').write_bytes(q.stdout + q.stderr)
assert q.returncode == 0
q = subprocess.run(['chroot', str(sdk), '/usr/bin/env', 'LD_LIBRARY_PATH='+prefix+'/usr/lib', '/private/'+name, '--self-test'], capture_output=True, timeout=15, check=True)
assert json.loads(q.stdout)['raw10_known_wire_vector_passed']
binary = host.PRIVATE / name
shutil.copyfile(sdk / 'private' / name, binary)
d = dict(stage=271, source_sha256=hashlib.sha256(text.encode()).hexdigest(), binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
         werror_clean=True, raw10_known_wire_vector_passed=True, manual_plan=plans, frames_per_phase=12, automatic_frames=180,
         expected_kernel_gain_units='integer real multipliers, baseline boot270 driver', no_pixels_written_by_probe=True)
(R / 'control-probe-build-validation.json').write_text(json.dumps(d, indent=2) + '\n')
print(json.dumps(d, indent=2))
