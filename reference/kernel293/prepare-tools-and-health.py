"""Compile bounded k293 probes and prepare read-only current health checks."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel292'
for tag in ['wb-params','optical']:
 p=ROOT/('samurai-'+tag+'.c');binary=host.PRIVATE/(tag+'-aarch64-private')
 q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi',str(p),'-o',str(binary)],capture_output=True)
 assert q.returncode==0,q.stderr.decode()
 assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
 flag='--pattern' if tag=='wb-params' else '--capture'
 assert subprocess.run(['qemu-aarch64',str(binary),flag,'/tmp/wrong-kernel-k293'],capture_output=True,timeout=10).returncode==3
 proof=json.loads((OLD/(tag+'-tool-validation.json')).read_text());proof.update(stage=293,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,not_run_on_phone=True)
 (ROOT/(tag+'-tool-validation.json')).write_text(json.dumps(proof,indent=2)+'\n')
s=(OLD/'final-health.py').read_text()
for line in s.splitlines():
 if line.startswith('assert json.loads((ROOT/'):s=s.replace(line+'\n','')
s=s.replace('k292-services-verified-private','k293-services-pre-transition-private').replace('k292-tools/final-health-private','k293-tools/pre-transition-health-private')
s=s.replace("ROOT/'final-health-validation.json'","ROOT/'pre-transition-health-validation.json'").replace('final-health-new-boot-private','pre-transition-health-private')
s=s.replace('standard_wb_params_verified=True','standard_wb_params_verified=False').replace('physical_scene_exposure_response_verified=True','physical_scene_exposure_response_verified=False')
(ROOT/'pre-transition-health.py').write_text(s)
print('Both bounded probes compiled; current k292 health checker prepared.')
