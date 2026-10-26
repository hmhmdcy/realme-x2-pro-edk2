"""Read current power graph and driver identities; no camera stream requested."""
from pathlib import Path
import hashlib
import json
import host

R = Path(__file__).resolve().parent
code = r'''
from pathlib import Path
import hashlib,json,os,subprocess
r=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k260-work/boot-id-private.txt').read_bytes()
proof=json.loads((r/'k265-package-transaction/summary.json').read_text())
for name,digest in proof['payload_sha256'].items():
 assert hashlib.sha256((Path('/')/name).read_bytes()).hexdigest()==digest
services=json.loads((r/'k265-services-current-private.json').read_text())
for i in services['new_processes']:
 assert (Path('/proc',str(i['pid']))/'stat').read_text().rsplit(')',1)[1].split()[19]==i['start_ticks']
root=Path('/sys/firmware/devicetree/base')
nodes={}
for p in root.rglob('compatible'):
 value=p.read_bytes()
 if any(x in value for x in [b'pm8008',b'imx319',b'imx471']):
  n=p.parent
  nodes[str(n.relative_to(root))]={x.name:x.read_bytes().hex() for x in n.iterdir() if x.is_file()}
modules={}
tree=Path('/usr/lib/modules')/os.uname().release
for mod in ['qcom_pm8008','qcom_pm8008_regulator','qcom_pm8008_imx319_lab','reset_realme_rmx1931_pm8008','imx319','imx471','qcom_camss']:
 p=Path('/sys/module',mod)
 if p.exists():
  path=subprocess.check_output(['modinfo','-n',mod],text=True).strip()
  modules[mod]=dict(sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),path=path,
   refcnt=(p/'refcnt').read_text().strip() if (p/'refcnt').exists() else None,
   parameters={x.name:x.read_text().strip() for x in (p/'parameters').glob('*') if x.is_file()})
pm={str(p):p.read_text().strip() for glob in ['*cci*/power/runtime_status','*camss*/power/runtime_status'] for p in Path('/sys/bus/platform/devices').glob(glob)}
for n in ['7-0010','9-0010']:
 p=Path('/sys/bus/i2c/devices',n,'power/runtime_status');pm[n]=p.read_text().strip();assert pm[n]=='suspended'
report=dict(stage=267,current_boot_verified=True,common_r3_verified=True,modules=modules,power=pm,device_tree_nodes=nodes,
 regulators=subprocess.check_output(['cat','/sys/kernel/debug/regulator/regulator_summary'],text=True),
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),no_stream_requested=True)
assert report['taint']==0
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/'baseline-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout)
print(json.dumps({k:d[k] for k in ['stage','current_boot_verified','common_r3_verified','modules','power','taint']},indent=2))
print(d['regulators'])
