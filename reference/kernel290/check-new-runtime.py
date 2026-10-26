"""Check the adopted kernel290, loaded module identities, standard PIX node and services."""
from pathlib import Path
import json
import host

ROOT=Path(__file__).resolve().parent
assert json.loads((ROOT/'postboot-identity-validation.json').read_text())['kernel_build']==290
code=r'''
from pathlib import Path
import hashlib,json,os,re,struct,subprocess
assert os.uname().version.startswith('#290 ') and os.uname().release=='7.3.0-rc6-rmx1931-samurai-k290+'
def note(p):
 b=Path(p).read_bytes();offset=struct.unpack_from('<Q',b,40)[0];size,count,index=struct.unpack_from('<HHH',b,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',b,offset+i*size) for i in range(count)];names=b[sections[index][4]:sections[index][4]+sections[index][5]]
 return next(b[s[4]:s[4]+s[5]] for s in sections if names[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
modules={}
for name in ['qcom_camss','i2c_qcom_cci','s5k3m5','s5kgw1','imx319','imx471','lc898219xi','qcom_pm8008','qcom_pm8008_regulator']:
 p=Path(subprocess.check_output(['modinfo','-n',name],text=True).strip());assert Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()==note(p)
 modules[name]=dict(loaded_note_matches_disk=True,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
sensors={}
for driver in ['s5kgw1','s5k3m5','imx319','imx471','lc898219xi']:
 found=[p for p in Path('/sys/bus/i2c/drivers',driver).glob('*') if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name)]
 assert len(found)==1;sensors[driver]=dict(device=found[0].name,state=(found[0]/'power/runtime_status').read_text().strip())
assert all(s['state']=='suspended' for s in sensors.values())
node=subprocess.check_output(['media-ctl','-d','/dev/media0','-e','msm_vfe0_video3'],text=True).strip()
formats=subprocess.check_output(['v4l2-ctl','-d',node,'--list-formats-ext'],text=True);assert "'NV12'" in formats and "[1]" not in formats
d=subprocess.check_output(['dmesg']);faults={k:d.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu_fault=b'gpu fault:',dsp_fatal=b'fatal error received').items()}
assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
services={name:subprocess.run(['rc-service',name,'status'],capture_output=True).returncode==0 for name in ['greetd','samurai-ssc','iio-sensor-proxy']};assert all(services.values())
print(json.dumps(dict(stage=290,kernel_build=290,release=os.uname().release,modules=modules,sensors=sensors,pix_node=node,pix_formats=formats,
 faults=faults,taint=0,pstore_files=len(list(Path('/sys/fs/pstore').glob('*'))),services=services)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=30)
r=json.loads(q.stdout);(ROOT/'postboot-runtime-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
