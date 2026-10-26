"""Prepare real-scene and ordinary camera tests for the newly adopted kernel292."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel291'
s=(OLD/'samurai-physical-pix.c').read_text().replace('samurai-k290+','samurai-k292+').replace('"#290 "','"#292 "')
p=ROOT/'samurai-optical.c';assert not p.exists();p.write_text(s);binary=host.PRIVATE/'optical-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(p),'-o',str(binary)],capture_output=True);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
assert subprocess.run(['qemu-aarch64',str(binary),'--capture','/tmp/wrong-kernel-optical292'],capture_output=True,timeout=10).returncode==3
proof=dict(stage=292,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),qemu_self_test_pass=True,wrong_kernel_guard_passed=True,planned_frames=18,sensor='imx319',sensor_pattern=0,csid_pattern=0,no_cpu_isp=True,no_userspace_mmio=True)
(ROOT/'optical-tool-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
worker=(OLD/'native-physical.py').read_text().replace('k291-physical-r1','k292-optical-r1').replace('k291-tools/physical-pix','k292-tools/optical').replace('k290-work','k292-work').replace("'#290 '","'#292 '").replace('samurai-k290+','samurai-k292+').replace('stage=291','stage=292').replace('kernel_build=290','kernel_build=292')
(ROOT/'native-optical.py').write_text(worker)
s=(OLD/'launch-physical.py').read_text().replace('physical-tool-validation','optical-tool-validation').replace('physical-pix-aarch64-private','optical-aarch64-private').replace('physical-pix','optical').replace('native-physical.py','native-optical.py').replace('k291-physical-r1','k292-optical-r1').replace('physical-worker','optical-worker').replace('physical-launch','optical-launch').replace('k291-tools','k292-tools').replace('k290-work','k292-work').replace('stage=291','stage=292')
s=s.replace("p=Path('/var/lib/samurai/k292-tools');assert not p.exists();p.mkdir(mode=0o700);(p/'optical.part').write_bytes(b'')","p=Path('/var/lib/samurai/k292-tools/optical.part');assert not p.exists();p.write_bytes(b'')")
(ROOT/'launch-optical.py').write_text(s)
s=(OLD/'poll-physical.py').read_text().replace('physical-launch','optical-launch').replace('k291-physical-r1','k292-optical-r1').replace('physical-poll','optical-poll').replace('physical-capture-validation','optical-capture-validation');(ROOT/'poll-optical.py').write_text(s)
s=(ROOT/'analyze-preboot-optical.py').read_text().replace('preboot-optical','optical').replace('actual_kernel_build=290','actual_kernel_build=292');(ROOT/'analyze-optical.py').write_text(s)
for name in ['native-four-camera-regression.py','launch-four-camera-regression.py','poll-four-camera-regression.py','inspect-regression-paths.py']:
 p=OLD/name
 if not p.exists():p=OLD.parent/'kernel290'/name
 s=p.read_text().replace('k291','k292').replace('k290-work','k292-work').replace("'#290 '","'#292 '").replace('samurai-k290+','samurai-k292+').replace('stage=291','stage=292').replace('four-camera291-','four-camera292-')
 if name=='inspect-regression-paths.py':s=s.replace('k290-four-camera','k292-four-camera').replace('stage=290','stage=292')
 (ROOT/name).write_text(s)
print('Prepared actual292 optical and standard four-camera tests.')
