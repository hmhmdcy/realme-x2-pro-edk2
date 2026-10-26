from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
proof=json.loads((here/'cpu-isp-capture-validation.json').read_text());assert proof['new_faults_zero'] and proof['no_drm_device_opened'] and sum(f['nonconstant'] for f in proof['frames'])==2
source=here.parents[1]/'linux-port/camera/configuration.yaml'
host.upload(source,'/tmp/k211-camera-configuration.yaml')
code=r'''
from pathlib import Path
import hashlib,json,os,pwd,stat,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k211-cpu-configuration';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-runtime/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
log=subprocess.check_output(['dmesg']);warnings=[line for line in log.splitlines() if b'WARNING:' in line]
assert len(warnings)==349 and all(b'__arm_lpae_unmap' in line and b'drivers/iommu/io-pgtable-arm.c:673' in line for line in warnings)
assert Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip()=='suspended'
user=pwd.getpwuid(10000)
for path in [Path(user.pw_dir)/'.config/libcamera/configuration.yaml',Path('/usr/share/libcamera/configuration.yaml'),Path('/etc/libcamera/configuration.yaml')]:assert not path.exists(),str(path)
data=Path('/tmp/k211-camera-configuration.yaml').read_bytes()
assert data.decode().endswith('version: 1\nconfiguration:\n  software_isp:\n    mode: cpu\n')
target=Path('/etc/libcamera/configuration.yaml');target.parent.mkdir(mode=0o755,exist_ok=True)
# mkdir mode is affected by umask077; the system configuration must be traversable.
os.chmod(target.parent,0o755)
with target.open('xb') as f:f.write(data)
os.chmod(target,0o644);assert target.read_bytes()==data
report=dict(stage=211,system_libcamera_cpu_configuration_installed=True,new_configuration_no_existing_user_or_system_file_overwritten=True,mode='cpu',sha256=hashlib.sha256(data).hexdigest(),configuration_effective_after_next_client_start=True,existing_wireplumber_not_restarted=True,known_gpu_warning_count=349,taint=512,no_camera_capture_in_deployment=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/'cpu-configuration-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'cpu-configuration-deployment-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
