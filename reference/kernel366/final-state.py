from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
assert json.loads((HERE/'camera-runtime-validation.json').read_text())['passed']
code=r'''
from pathlib import Path
import hashlib,json,struct,subprocess
services={};workers=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  if (p/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z':continue
  name=(p/'comm').read_text().strip()
  if name in ['pipewire','wireplumber']:services.setdefault(name,[]).append(dict(pid=int(p.name),uid=p.stat().st_uid))
  args=(p/'cmdline').read_bytes().split(b'\0')
  if any(a.startswith((b'/var/lib/samurai/k363-',b'/var/lib/samurai/k364-',b'/var/lib/samurai/k365-',b'/var/lib/samurai/k366-')) and a.endswith((b'/worker.py',b'/quiesce-worker.py')) for a in args):workers.append(int(p.name))
 except OSError:pass
module=Path(subprocess.check_output(['modinfo','-n','qcom_camss'],text=True).strip())
names=['acb3000.camss','ac4a000.cci','ac4b000.cci'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
module_facts={}
for name in module_names:
 path=Path(subprocess.check_output(['modinfo','-n',name],text=True).strip());raw=path.read_bytes()
 shoff=struct.unpack_from('<Q',raw,40)[0];entry,count,strings=struct.unpack_from('<HHH',raw,58)
 headers=[raw[shoff+i*entry:shoff+(i+1)*entry] for i in range(count)]
 off,size=struct.unpack_from('<QQ',headers[strings],24);table=raw[off:off+size];note=None
 for header in headers:
  idx=struct.unpack_from('<I',header)[0];label=table[idx:].split(b'\0',1)[0]
  if label==b'.note.gnu.build-id':
   off,size=struct.unpack_from('<QQ',header,24);note=raw[off:off+size]
 loaded=Path('/sys/module')/name;disk_note=loaded/'notes/.note.gnu.build-id'
 module_facts[name]=dict(sha256=hashlib.sha256(raw).hexdigest(),loaded=loaded.exists(),loaded_note_matches_disk=disk_note.exists() and disk_note.read_bytes()==note,intree='Y',parameters={p.name:p.read_text().strip() for p in (loaded/'parameters').glob('*') if p.is_file()})
facts=dict(kernel=subprocess.check_output(['uname','-r'],text=True).strip(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 camss_note_sha256=sha(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id')),camss_disk_sha256=sha(module),services=services,workers=workers,
 platforms={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in names},
 rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))},
 icp_modules=[p.name for p in Path('/sys/module').glob('*icp*')],
 temporary_firmware_absent=not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists(),
 temporary_icp_node_absent=not Path('/sys/firmware/devicetree/base/soc@0/samurai-icp356-boot@ac10000').exists(),
 static_icp_status=Path('/sys/firmware/devicetree/base/soc@0/icp@ac10000/status').read_bytes().rstrip(b'\0').decode(),deployed_camera_modules=module_facts)
print(json.dumps(facts))
'''
names=list(json.loads((HERE.parents[1]/'linux-port/camera/kernel/source-lock.json').read_text())['deployed_camera_modules'])
d=json.loads(host.ssh('python3 -c '+shlex.quote('module_names='+repr(names)+'\n'+code),timeout=30).stdout)
d.update(stage=366,ssh='strict_original_key_usb',kernel_image_stage=363,firmware_boot_stage=366,dt_stage=365,installed_userspace_stage=362)
d['passed']=bool(d['taint']==0 and not d['workers'] and not d['icp_modules'] and d['temporary_firmware_absent'] and d['temporary_icp_node_absent'] and d['static_icp_status']=='disabled' and
 d['camss_note_sha256']=='1e78064da626b1dd91fc82c183abd96b5fb98f95e11a8eb7b760b9a138095dae' and all(x['loaded_note_matches_disk'] for x in d['deployed_camera_modules'].values()) and
 all(v=='suspended' for v in d['platforms'].values()) and all(v==dict(state='disabled',users=0) for v in d['rails'].values()) and
 all(len(d['services'].get(n,[]))==1 and d['services'][n][0]['uid']==10000 for n in ['pipewire','wireplumber']))
(HERE/'final-state-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2));assert d['passed']
