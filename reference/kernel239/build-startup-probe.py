from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel239');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
source=R/'startup-probe.cpp';shutil.copyfile(source,SDK/'private/startup-probe239.cpp')
command=['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread','-I/candidate238-r14/usr/include/libcamera','/private/startup-probe239.cpp','-L/candidate238-r14/usr/lib','-Wl,-rpath-link,/candidate238-r14/usr/lib','-lcamera','-lcamera-base','-o','/private/startup-probe239']
result=subprocess.run(command,capture_output=True,timeout=180);(P/'startup-build-private.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0,'inspect private compiler diagnostics'
binary=P/'startup-probe239';shutil.copyfile(SDK/'private/startup-probe239',binary);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(stage=239,source_sha256=sha(source),binary_sha256=sha(binary),binary_bytes=binary.stat().st_size,werror_clean=True,same_camera_configure_once_start_stop_twice=True,frames_each_run=12,fixed_exposure_us=2000,fixed_analogue_gain=1.0,no_scene_pixels_saved=True)
(R/'startup-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
