"""Read current runtime and standard entity controls before physical PIX work."""
from pathlib import Path
import json
import host
ROOT=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os,re,subprocess
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k290+' and os.uname().version.startswith('#290 ')
runtime={}
for name in ['s5kgw1','s5k3m5','imx319','imx471','lc898219xi']:
 p=next(p for p in Path('/sys/bus/i2c/drivers',name).iterdir() if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name))
 runtime[name]=(p/'power/runtime_status').read_text().strip()
assert all(s=='suspended' for s in runtime.values())
graph=subprocess.check_output(['media-ctl','-d','/dev/media0','-p'],text=True)
controls={}
for name in ['imx319','msm_csid0','msm_vfe0_pix']:
 entity=next(x for x in graph.split('- entity ') if (name+' ' in x.splitlines()[0] or name+':' in x.splitlines()[0]))
 node=re.search(r'device node name (\S+)',entity)[1]
 q=subprocess.run(['v4l2-ctl','-d',node,'--list-ctrls-menus','--get-subdev-fmt','pad=0'],capture_output=True,text=True)
 controls[name]=dict(node=node,exit=q.returncode,stdout=q.stdout,stderr=q.stderr)
kernel=subprocess.check_output(['dmesg']);fault={n:kernel.count(s) for n,s in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received').items()}
assert not any(fault.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
print(json.dumps(dict(stage=291,kernel_build=290,runtime=runtime,graph=graph,controls=controls,faults=fault)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
data=json.loads(q.stdout);(host.PRIVATE/'preflight-private.json').write_bytes(q.stdout)
(ROOT/'runtime-preflight-validation.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data,indent=2))
