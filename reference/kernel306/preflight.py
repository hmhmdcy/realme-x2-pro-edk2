"""Revalidate the phone identity and measured sensor configuration without streaming."""
from pathlib import Path
import json
import host
HERE=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,re,subprocess
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0'
assert os.uname().version.startswith('#298 ')
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/s5k3m5.ko'
assert hashlib.sha256(module.read_bytes()).hexdigest()=='d1a85e75b9344423097c8189ed65a0320abcb3f7ba3d5fdac34e3c8758f056c9'
assert hashlib.sha256(Path('/sys/module/s5k3m5/notes/.note.gnu.build-id').read_bytes()).hexdigest()=='46cdb06ba55ca6f10e3f8c765acedf2c88fb2a2b288112a8a43a5083b4e15538'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
devices=[p for p in Path('/sys/bus/i2c/drivers/s5k3m5').iterdir() if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name)]
assert len(devices)==1;device=devices[0]
node=next('/dev/'+p.name for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='s5k3m5 '+device.name)
q=subprocess.run(['v4l2-ctl','-d',node,'--list-ctrls','--get-subdev-fmt','pad=0'],capture_output=True,text=True,timeout=10)
assert q.returncode==0
out=Path('/var/lib/samurai/k306-preflight-r1');assert not out.exists();out.mkdir(mode=0o700)
(out/'sensor-controls-private.txt').write_text(q.stdout+q.stderr)
(out/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
for p in Path('/proc').glob('[0-9]*'):
 try:
  fields=(p/'stat').read_text().rsplit(')',1)[1].split()
  cmd=(p/'cmdline').read_bytes()
  if fields[0]!='Z' and b'/var/lib/samurai/k303-' in cmd:raise RuntimeError('Prior camera worker still live')
 except (FileNotFoundError,ProcessLookupError):pass
print(json.dumps(dict(stage=306,same305_guard=True,kernel_build=298,taint=0,loaded_sensor_module_verified=True,
 device=device.name,node=node,camera_id='/base'+str((device/'of_node').resolve()).split('/base',1)[1],
 controls=q.stdout)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25)
d=json.loads(q.stdout);(host.PRIVATE/'preflight-private.json').write_text(json.dumps(d,indent=2)+'\n')
(HERE/'preflight-validation.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d,indent=2))
