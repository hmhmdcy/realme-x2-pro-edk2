"""Authenticate current boot and candidate/idle state before diagnostics."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess
os.umask(0o077);r=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(r/'k236-runtime/boot-id-private.txt').read_bytes()
out=r/'k239-baseline';assert not out.exists();out.mkdir(mode=0o700);(out/'boot-id-private.txt').write_bytes(boot)
for name in ['k238-controlled-rear-r14','k238-controlled-rear-r14-r2','k238-controlled-rear-rgb-r14','k238-controlled-rear-rgb-r14-r2','k238-vendor-audit','k238-vendor-followup']:
 assert json.loads((r/name/'state-private.json').read_text())['state']=='terminal'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
for node in ['7-0010','9-0010']:assert Path('/sys/bus/i2c/devices',node,'power/runtime_status').read_text().strip()=='suspended'
for node in ['ac4a000.cci','ac4b000.cci','acb3000.camss']:assert Path('/sys/bus/platform/devices',node,'power/runtime_status').read_text().strip()=='suspended'
assert Path('/lib/apk/db/installed').read_bytes()==(r/'k236-baseline/installed-before-private.txt').read_bytes()
lock=json.loads((r/'k238-tools/candidate-runtime-lock-private.json').read_text());prefix=Path('/run/samurai-camera238-r14')
for name,item in lock['files'].items():
 p=prefix/name
 if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
 else:assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
assert b'mode: cpu' in (prefix/'config-enabled/libcamera/configuration.yaml').read_bytes()
assert json.loads((r/'k238-candidate-permissions-fix/summary.json').read_text())['uid10000_cpu_config_read_verified']
clients=0
for proc in Path('/proc').glob('[0-9]*'):
 for fd in (proc/'fd').glob('*'):
  try:target=os.readlink(fd)
  except OSError:continue
  if target.startswith(('/dev/video','/dev/v4l-subdev','/dev/media')):clients+=1
assert clients==0
assert not any(p.name.startswith(('k236','k238','k239')) for p in Path('/sys/kernel/tracing/instances').iterdir())
assert not any('k238' in line for line in Path('/proc/self/mountinfo').read_text().splitlines())
(r/'k239-tools').mkdir(mode=0o700)
(out/'dmesg-private.txt').write_bytes(subprocess.check_output(['dmesg']))
report=dict(stage=239,current236_boot_verified=True,all238_workers_terminal=True,camera_idle_no_other_clients=True,r14_ram_payload_files_verified=len(lock['files']),installed_r13_r8_package_database_unchanged=True,temporary_traces_mounts_absent=True,taint=0,previous_goal_turn_classification='progress',no_capture_yet=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
result=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/'baseline-host-private.log').write_bytes(result.stdout+result.stderr)
report=json.loads(result.stdout);(R/'baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
