"""Confirm the previous format callbacks fail the new capability check."""
from pathlib import Path
import json,resource,subprocess
import host
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
baseline=subprocess.check_output(['git','-C',str(TREE),'show','15c8639d8badf5d4146bfd1b2c2fcb2460a137e5:drivers/media/platform/qcom/camss/camss-vfe.c'],text=True)
s=(host.PRIVATE/'pad-params-tests-private.c').read_text()
def function(source,signature):
 start=source.index(signature);return source[start:source.index('\n}',start)+2]
for signature in ['__vfe_get_format(','static int vfe_enum_mbus_code(','static int vfe_enum_frame_size(']:
 old=function(s,signature);s=s.replace(old,function(baseline,signature),1)
p=host.PRIVATE/'pad-parent-negative-private.c';p.write_text(s);binary=p.with_suffix('')
q=subprocess.run(['gcc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(p),'-o',str(binary)],capture_output=True);assert q.returncode==0,q.stderr.decode()
def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
q=subprocess.run([str(binary)],capture_output=True,timeout=20,preexec_fn=no_core)
(host.PRIVATE/'pad-parent-negative-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==-6 and b'vfe_get_format(&sd,&state,&format)' in q.stderr,q.stderr.decode()
report=dict(stage=292,previous_callbacks_reproduced_undeclared_pad_format_acceptance=True,expected_assertion_failure=True,exit=q.returncode,new_callbacks_passed=True)
(ROOT/'pad-parent-negative-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
