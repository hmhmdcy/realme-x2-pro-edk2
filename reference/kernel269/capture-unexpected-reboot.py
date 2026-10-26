"""Read the newly booted, strictly authenticated device and preserve crash logs."""
from pathlib import Path
import base64,hashlib,importlib.util,json,re
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R.parent/'kernel267/host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
out=P/'unexpected-reboot-r1';out.mkdir(mode=0o700)
code=r'''
from pathlib import Path
import base64,hashlib,json,os,subprocess
assert 'realme,samurai' in Path('/sys/firmware/devicetree/base/compatible').read_bytes().decode().split('\0')
files={}
for directory in ['/sys/fs/pstore','/var/lib/systemd/pstore']:
 for p in Path(directory).glob('*'):
  if p.is_file():files[str(p)]=base64.b64encode(p.read_bytes()).decode()
for name in ['/proc/last_kmsg','/proc/cmdline','/var/log/messages','/var/log/dmesg','/sys/kernel/boot_reason']:
 p=Path(name)
 if p.is_file():files[name]=base64.b64encode(p.read_bytes()).decode()
files['current-dmesg']=base64.b64encode(subprocess.check_output(['dmesg'])).decode()
mods={}
for name in ['qcom_pm8008','qcom_pm8008_regulator','imx319','imx471','qcom_camss']:
 q=subprocess.run(['modinfo','-n',name],capture_output=True,text=True)
 p=Path(q.stdout.strip())
 mods[name]=dict(loaded=Path('/sys/module',name).exists(),sha256=hashlib.sha256(p.read_bytes()).hexdigest() if q.returncode==0 and p.is_file() else None)
print(json.dumps(dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),release=os.uname().release,
 uptime=Path('/proc/uptime').read_text().strip(),taint=Path('/proc/sys/kernel/tainted').read_text().strip(),
 compatible=Path('/sys/firmware/devicetree/base/compatible').read_bytes().decode().strip('\0').split('\0'),
 modules=mods,rotation_rule_exists=Path('/etc/udev/rules.d/99-realme-rmx1931-sensors.rules').exists(),files=files)))
'''
q=h.raw_ssh('python3 -',input=code.encode(),timeout=45);(out/'response-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
old=json.loads((P.parent/'kernel267/postboot-verified-private.json').read_text());assert old['boot_id']!=d['boot_id']
inventory=[]
for i,(name,data) in enumerate(d.pop('files').items()):
 raw=base64.b64decode(data);p=out/('log-'+str(i)+'-private.bin');p.write_bytes(raw)
 inventory.append(dict(source=name,private_file=p.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d['log_inventory']=inventory;(out/'identity-private.json').write_text(json.dumps(d,indent=2)+'\n')
report=dict(stage=269,unexpected_reboot_confirmed=True,strict_original_ssh_key=True,release=d['release'],uptime_seconds=float(d['uptime'].split()[0]),
 current_taint=d['taint'],modules=d['modules'],rotation_rule_was_not_installed=not d['rotation_rule_exists'],logs=inventory,
 no_camera_started_and_no_restart_requested=True)
(R/'unexpected-reboot-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
