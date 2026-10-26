"""Build a finite, same-request RAW/RGB exposure-response diagnostic."""
from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel270');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
text=(R.parent/'kernel240/upright-paired-probe.cpp').read_text()
changes=[('/base/soc@0/cci@ac4a000/i2c-bus@1/camera@10','/base/soc@0/cci@ac4b000/i2c-bus@0/camera@2d'),
 ('imx319 7-0010','s5k3m5 8-002d'),('"imx319"','"s5k3m5"'),('"1624"','"2048"'),('"1224"','"1536"'),
 ('rgb.size = {1624, 1224}','rgb.size = {2048, 1536}'),('raw.size = {1632, 1224}','raw.size = {2104, 1560}'),
 ('Size(1624,1224)','Size(2048,1536)'),('Size(1632,1224)','Size(2104,1560)'),('formats::SRGGB10_CSI2P','formats::SGRBG10_CSI2P')]
for a,b in changes:assert a in text,a;text=text.replace(a,b)
source=R/'telephoto-paired-probe.cpp';source.write_text(text)
dest=SDK/'private/telephoto-paired-probe270.cpp';assert not dest.exists();shutil.copyfile(source,dest)
prefix='/candidate239-r15'
q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-pthread',
 '-I'+prefix+'/usr/include/libcamera','/private/telephoto-paired-probe270.cpp','-L'+prefix+'/usr/lib','-Wl,-rpath-link,'+prefix+'/usr/lib',
 '-lcamera','-lcamera-base','-o','/private/telephoto-paired-probe270'],capture_output=True,timeout=150)
(P/'paired-probe-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0
q=subprocess.run(['chroot',str(SDK),'/usr/bin/env','LD_LIBRARY_PATH='+prefix+'/usr/lib','/private/telephoto-paired-probe270','--self-test'],capture_output=True,timeout=15)
assert q.returncode==0 and json.loads(q.stdout)['raw10_known_wire_vector_passed']
binary=P/'telephoto-paired-probe270';shutil.copyfile(SDK/'private/telephoto-paired-probe270',binary)
report=dict(stage=270,source_sha256=hashlib.sha256(text.encode()).hexdigest(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,
 werror_clean=True,raw10_known_wire_vector_passed=True,paired_requests=24,exposure_phases_us=[2000,32000],analogue_gain=1,
 raw_dimensions=[2104,1560],processed_dimensions=[2048,1536],scene_pixels_not_saved_by_probe=True)
(R/'paired-probe-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
