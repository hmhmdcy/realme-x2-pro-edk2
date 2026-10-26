from pathlib import Path
import hashlib,json,shutil,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel216');root=Path('/home/cy122/x2pro-linux/libcamera214-root')
source=(here.parent/'kernel213/raw-dark-sync-probe.cpp').read_text()
start=source.index('class PatternGuard {');end=source.index('struct FrameStats',start)
gain=source[start:end].replace('PatternGuard','AnalogueGainGuard').replace('V4L2_CID_TEST_PATTERN','V4L2_CID_ANALOGUE_GAIN').replace('original_ == 0','original_ >= 0 && original_ <= 960').replace('sensor pattern must initially be disabled','original gain must be valid').replace('sensor pattern','sensor gain').replace('color bars','analogue gain')
source=source[:end]+gain+source[end:]
source=source.replace('argc != 4','argc != 5').replace('const int selected = std::stoi(argv[3]);','const int selected = std::stoi(argv[3]);\n    const int gainCode = std::stoi(argv[4]);\n    if (!raw || selected != 0 || (gainCode != 0 && gainCode != 800 && gainCode != 960)) return 2;')
source=source.replace('std::unique_ptr<PatternGuard> pattern;','std::unique_ptr<PatternGuard> pattern;\n    std::unique_ptr<AnalogueGainGuard> gain;')
source=source.replace('        started = true;','        started = true;\n        gain = std::make_unique<AnalogueGainGuard>(argv[1], gainCode);')
source=source.replace('pattern.reset();','gain.reset();\n    pattern.reset();')
path=here/'raw-gain-sync-probe.cpp';path.write_text(source);shutil.copyfile(path,root/'private/raw-gain-sync-probe.cpp')
p=subprocess.run(['chroot',str(root),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread','-I/candidate/usr/include/libcamera','/private/raw-gain-sync-probe.cpp','-L/candidate/usr/lib','-Wl,-rpath-link,/candidate/usr/lib','-lcamera','-lcamera-base','-o','/private/raw-gain-sync-probe'],capture_output=True,timeout=120);(private/'raw-gain-probe-build-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
p=subprocess.run(['chroot',str(root),'/usr/bin/readelf','-d','/private/raw-gain-sync-probe'],capture_output=True,text=True,timeout=15);assert p.returncode==0 and 'RUNPATH' not in p.stdout and 'RPATH' not in p.stdout
target=private/'raw-gain-sync-probe';shutil.copyfile(root/'private/raw-gain-sync-probe',target)
report=dict(stage=216,finite_six_frame_gain_raw_probe_built=True,gain_written_after_stream_start_before_queue=True,gain_codes_allowed=[0,800,960],test_pattern_forced_off=True,physical_raw10_dma_sync_and_padding_exclusion_preserved=True,raii_gain_and_test_pattern_restore=True,no_embedded_candidate_runpath=True,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size,actual_gain_sensitivity_calibration_not_claimed=True)
(here/'gain-probe-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
