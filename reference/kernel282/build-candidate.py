"""Build the prerequisite or output candidate with diagnostics retained."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
import host

ROOT = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BUILD = Path('/home/cy122/x2pro-linux/camera279-isp-build-r1')
assert len(sys.argv) == 2 and sys.argv[1] in ['prereq','output','output-final']
name = sys.argv[1]
marker = host.PRIVATE / (name + '-build-state-private.json')
log = BUILD / ('vfe282-' + name + '-werror-private.log')
assert not marker.exists() and not log.exists()
env = dict(os.environ, PATH='/home/cy122/.cargo/bin:' + os.environ['PATH'],
           RUSTUP_HOME='/home/cy122/.rustup', KBUILD_BUILD_VERSION='282',
           KBUILD_BUILD_USER='builder', KBUILD_BUILD_HOST='samurai')
command = ['make','-C',str(TREE),'O='+str(BUILD),'ARCH=arm64',
           'CROSS_COMPILE=aarch64-linux-gnu-','-j3','W=1','KCFLAGS=-Werror',
           'drivers/media/platform/qcom/camss/qcom-camss.o','qcom/sm8150-samurai.dtb']
start = time.monotonic()
state = dict(stage=282,phase=name,pid=os.getpid(),terminal=False,command=command)
with log.open('xb') as output:
    child = subprocess.Popen(command,env=env,stdout=output,stderr=subprocess.STDOUT)
    state['child_pid']=child.pid
    marker.write_text(json.dumps(state,indent=2)+'\n')
    result=child.wait()
state.update(terminal=True,exit=result,seconds=round(time.monotonic()-start,2))
marker.write_text(json.dumps(state,indent=2)+'\n')
assert result == 0, 'Read terminal build log before follow-up'
diagnostics=[line for line in log.read_text().splitlines() if 'warning:' in line.lower() or 'error:' in line.lower()]
assert not diagnostics,diagnostics
dtb=BUILD/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'
assert hashlib.sha256(dtb.read_bytes()).hexdigest()=='dcdd74ec903520c7023fa28badcb293b2e4e26ee5bac639497c63d53536b2c8d'
report={k:v for k,v in state.items() if k not in ['pid','child_pid']}
report.update(diagnostics=diagnostics,camera_component_objects=31 if name=='prereq' else 32,
              camss_object_sha256=hashlib.sha256((BUILD/'drivers/media/platform/qcom/camss/qcom-camss.o').read_bytes()).hexdigest(),
              dtb_sha256=hashlib.sha256(dtb.read_bytes()).hexdigest(),
              no_full_kernel_link_or_hardware_isp_test=True,not_deployed=True)
(ROOT/(name+'-build-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
