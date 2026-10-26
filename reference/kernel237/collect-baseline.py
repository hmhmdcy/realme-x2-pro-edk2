"""Fresh small capture baseline, no partition reread or radio control."""
from pathlib import Path
import json
import host

code = r'''
from pathlib import Path
import hashlib,json,os,struct,subprocess
os.umask(0o077)
root=Path('/var/lib/samurai'); boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot==(root/'k236-runtime/boot-id-private.txt').read_bytes()
assert json.loads((root/'k236-lab-fix/state-private.json').read_text())['exit_code']==0
out=root/'k237-baseline';assert not out.exists();out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
tree=Path('/usr/lib/modules')/os.uname().release
def note(data):
 off=struct.unpack_from('<Q',data,40)[0];size,count,idx=struct.unpack_from('<HHH',data,58)
 secs=[struct.unpack_from('<IIQQQQIIQQ',data,off+i*size) for i in range(count)]
 strings=data[secs[idx][4]:secs[idx][4]+secs[idx][5]]
 found=[data[s[4]:s[4]+s[5]] for s in secs if strings[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id']
 assert len(found)==1;return found[0]
expected=json.loads((root/'k236-lab-fix/module-inventory-after-private.json').read_text())
modules={}
for mod,rel in [('qcom_pm8008','drivers/mfd/qcom-pm8008.ko'),('qcom_pm8008_imx319_lab','drivers/regulator/qcom-pm8008-imx319-lab.ko'),('imx319','drivers/media/i2c/imx319.ko'),('imx471','drivers/media/i2c/imx471.ko'),('qcom_camss','drivers/media/platform/qcom/camss/qcom-camss.ko')]:
 data=(tree/'kernel'/rel).read_bytes();digest=hashlib.sha256(data).hexdigest()
 assert digest==expected['kernel/'+rel] and Path('/sys/module',mod,'notes/.note.gnu.build-id').read_bytes()==note(data)
 modules[mod]=digest
devices=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/ac4a000.cci','/sys/bus/platform/devices/ac4b000.cci','/sys/bus/platform/devices/acb3000.camss']
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in devices)
assert Path(devices[0],'driver').resolve().name=='imx319'
assert Path(devices[1],'driver').resolve().name=='imx471'
for bus,ofid in [('7-0010','/soc@0/cci@ac4a000/i2c-bus@1/camera@10'),('9-0010','/soc@0/cci@ac4b000/i2c-bus@1/camera@10')]:
 assert str(Path('/sys/bus/i2c/devices',bus,'of_node').resolve()).endswith('/base'+ofid)
nodes={p.name:(p/'name').read_text().strip() for p in Path('/sys/class/video4linux').glob('v4l-subdev*')}
assert list(nodes.values()).count('imx319 7-0010')==list(nodes.values()).count('imx471 9-0010')==1
for node,name in nodes.items():
 if name.startswith(('imx319','imx471','msm_csid')):
  p=subprocess.run(['v4l2-ctl','-d','/dev/'+node,'--list-ctrls'],capture_output=True,timeout=10)
  assert p.returncode==0;(out/(node+'-controls-private.txt')).write_bytes(p.stdout+p.stderr)
graph=subprocess.check_output(['media-ctl','-d','/dev/media0','-p'],timeout=15)
(out/'media-private.txt').write_bytes(graph)
clients=[]
for p in Path('/proc').glob('[0-9]*'):
 for fd in (p/'fd').glob('*'):
  try:target=os.readlink(fd)
  except OSError:continue
  if target.startswith(('/dev/video','/dev/v4l-subdev','/dev/media')):clients.append(dict(pid=int(p.name),target=target))
assert not clients,clients
rails={}
for p in Path('/sys/class/regulator').glob('regulator.*'):
 name=(p/'name').read_text().strip()
 if name.startswith(('cam-front-','cam-rear-')) or Path('/sys/bus/i2c/devices/1-0004').resolve() in p.resolve().parents:
  rails[name]={k:(p/k).read_text().strip() for k in ['state','num_users','microvolts']}
  if name.startswith(('cam-front-','cam-rear-')):assert rails[name]['state']=='disabled' and rails[name]['num_users']=='0'
(out/'rails-private.json').write_text(json.dumps(rails,indent=2)+'\n')
for label,path in [('clocks','/sys/kernel/debug/clk/clk_summary'),('gpio','/sys/kernel/debug/gpio'),('regulators','/sys/kernel/debug/regulator/regulator_summary')]:
 (out/(label+'-private.txt')).write_text(Path(path).read_text())
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log)
faults={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',bt=b'Frame reassembly failed').items()}
assert not any(faults.values()) and not any(p.read_text().strip() for p in Path('/sys/module').glob('*/taint'))
assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes()
report=dict(stage=237,current236_boot=True,default_and_loaded_modules=modules,sensor_nodes={k:v for k,v in nodes.items() if v.startswith(('imx319','imx471'))},both_of_nodes_verified=True,all_camera_devices_suspended=True,no_camera_clients=True,rails_saved=True,taint=0,faults=faults,no_capture_yet=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=55)
(host.PRIVATE/'baseline-host-private.log').write_bytes(r.stdout+r.stderr)
report=json.loads(r.stdout)
(Path(__file__).resolve().parent/'baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
