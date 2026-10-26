"""Correct only the missing telephoto module after the first build is terminal."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import host

ROOT=Path(__file__).resolve().parent
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BUILD=Path('/home/cy122/x2pro-linux/camera279-isp-build-r1')
state=json.loads((host.PRIVATE/'full-kernel-build-state-private.json').read_text())
assert state['terminal'] and state['exit']==-15
assert not Path('/proc',str(state['pid'])).exists() and not Path('/proc',str(state['child_pid'])).exists()
remaining=[]
for process in Path('/proc').iterdir():
    if not process.name.isdigit():
        continue
    try:
        cwd=(process/'cwd').resolve(strict=True)
        comm=(process/'comm').read_text().strip()
        if (cwd==BUILD or BUILD in cwd.parents) and comm not in ['python3']:
            remaining.append(dict(pid=int(process.name),comm=comm))
    except (FileNotFoundError,PermissionError,ProcessLookupError):
        pass
assert not remaining, remaining
before=(BUILD/'.config').read_bytes()
assert b'# CONFIG_VIDEO_S5K3M5 is not set\n' in before
(host.PRIVATE/'full-config-before-private').write_bytes(before)
if (BUILD/'.config.old').exists():
    (host.PRIVATE/'full-config-old-before-private').write_bytes((BUILD/'.config.old').read_bytes())
subprocess.run([str(TREE/'scripts/config'),'--file',str(BUILD/'.config'),'--module','VIDEO_S5K3M5'],check=True)
env=dict(os.environ,PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
run=subprocess.run(['make','-C',str(TREE),'O='+str(BUILD),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-',
                    'olddefconfig'],env=env,capture_output=True,text=True)
(host.PRIVATE/'full-config-olddefconfig-private.log').write_text(run.stdout+run.stderr)
assert run.returncode==0,run.stdout+run.stderr
after=(BUILD/'.config').read_bytes()
removed=sorted(set(before.decode().splitlines())-set(after.decode().splitlines()))
added=sorted(set(after.decode().splitlines())-set(before.decode().splitlines()))
assert removed==['# CONFIG_VIDEO_S5K3M5 is not set'] and added==['CONFIG_VIDEO_S5K3M5=m'],(removed,added)
initial=json.loads((host.PRIVATE/'full-kernel-build-result-private.json').read_text())
report=dict(stage=282,first_build_terminal=True,first_exit=initial['exit'],intentional_stop=True,
    reason='initial full configuration omitted existing telephoto driver',
    no_old_build_processes_remaining=True,before_config_sha256=hashlib.sha256(before).hexdigest(),
    corrected_config_sha256=hashlib.sha256(after).hexdigest(),removed=removed,added=added,
    olddefconfig_exit=run.returncode,first_build_diagnostics=initial['diagnostic_count'],
    first_camss_diagnostics=initial['camss_diagnostics'],
    first_attempt_not_a_successful_full_build=True,no_phone_changes=True)
(ROOT/'full-config-correction-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
