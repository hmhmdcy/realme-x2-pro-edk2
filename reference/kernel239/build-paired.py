from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel239');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert json.loads((R/'fixed-rgb-validation.json').read_text())['diagnostic_capture_completed']
text=(R/'fixed-rgb-probe.cpp').read_text().split('struct FrameStats {',1)[0]+(R/'paired-probe-body.cpp').read_text()
source=R/'paired-probe.cpp'
if source.exists():
 assert not (R/'paired-build-validation.json').exists() and not (P/'paired-build-first-failure-private.log').exists()
 oldlog=P/'paired-build-private.log';assert b"has no member named 'at'" in oldlog.read_bytes()
 shutil.copyfile(source,P/'paired-probe-first-build-private.cpp');shutil.copyfile(oldlog,P/'paired-build-first-failure-private.log')
 (R/'paired-first-build-failure-validation.json').write_text(json.dumps(dict(stage=239,compile_failed_before_native_use=True,libcamera_span_has_no_at=True,corrected_with_checked_plane_accessor=True),indent=2)+'\n')
source.write_text(text);shutil.copyfile(source,SDK/'private/paired-probe239.cpp')
command=['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread','-I/candidate238-r14/usr/include/libcamera','/private/paired-probe239.cpp','-L/candidate238-r14/usr/lib','-Wl,-rpath-link,/candidate238-r14/usr/lib','-lcamera','-lcamera-base','-o','/private/paired-probe239']
result=subprocess.run(command,capture_output=True,timeout=180);(P/'paired-build-private.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0,'inspect private paired compiler diagnostics'
test=subprocess.run(['chroot',str(SDK),'/usr/bin/env','LD_LIBRARY_PATH=/candidate238-r14/usr/lib','/private/paired-probe239','--self-test'],capture_output=True,timeout=15);(P/'paired-selftest-private.log').write_bytes(test.stdout+test.stderr);assert test.returncode==0 and json.loads(test.stdout)['raw10_known_wire_vector_passed']
binary=P/'paired-probe239';shutil.copyfile(SDK/'private/paired-probe239',binary);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(stage=239,source_sha256=sha(source),binary_sha256=sha(binary),binary_bytes=binary.stat().st_size,werror_clean=True,raw10_known_wire_vector_test_passed=True,frames=12,same_request_two_streams=True,sequence_and_timestamp_equality_required=True,all_active_pixels_counted=True,no_scene_images_saved=True)
(R/'paired-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
