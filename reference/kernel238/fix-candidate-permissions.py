from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,os,pwd,stat,subprocess,sys
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
context=r/'k238-controlled-rear-r14';assert json.loads((context/'state-private.json').read_text())['state']=='terminal'
summary=json.loads((context/'summary.json').read_text());assert summary['program_exit']==1 and all(summary[k] for k in ['all_formats_restored','media_graph_restored','sensor_controls_restored','rails_unchanged','camera_devices_suspended','mclk1_mclk2_disabled','trace_instance_removed'])
out=r/'k238-candidate-permissions-fix';assert not out.exists();out.mkdir(mode=0o700)
target=Path('/run/samurai-camera238-r14');paths=[target/'config-enabled',target/'config-enabled/libcamera'];before={str(p.relative_to(target)):stat.S_IMODE(p.stat().st_mode) for p in paths}
assert before=={'config-enabled':0o700,'config-enabled/libcamera':0o700}
for p in paths:p.chmod(0o755)
user=pwd.getpwuid(10000)
def demote():os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
p=subprocess.run([sys.executable,'-c',"from pathlib import Path;assert b'mode: cpu' in Path('/run/samurai-camera238-r14/config-enabled/libcamera/configuration.yaml').read_bytes()"],preexec_fn=demote,capture_output=True,timeout=5)
(out/'uid10000-config-read-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
report=dict(stage=238,before_modes=before,after_modes={str(p.relative_to(target)):stat.S_IMODE(p.stat().st_mode) for p in paths},uid10000_cpu_config_read_verified=True,first_controlled_failure_and_cleanup_preserved=True,no_new_capture_yet=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=15);(host.PRIVATE/'permissions-fix-host-private.log').write_bytes(r.stdout+r.stderr);report=json.loads(r.stdout)
(Path(__file__).resolve().parent/'candidate-permissions-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
