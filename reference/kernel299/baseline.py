"""Fresh identity and idle-resource check before existing-interface experiments."""
from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent
tree='/home/cy122/x2pro-linux/camera279-isp-kernel'
assert subprocess.check_output(['git','-C',tree,'rev-parse','HEAD'],text=True).strip()=='c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117'
assert not subprocess.check_output(['git','-C',tree,'status','--porcelain'])
code=r'''
from pathlib import Path
import json,os,re,subprocess
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k298+' and os.uname().version.startswith('#298 ')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k298-work/boot-id-private.txt').read_bytes()
runtime={}
for driver in ['s5kgw1','s5k3m5','imx319','imx471','lc898219xi']:
 for p in Path('/sys/bus/i2c/drivers',driver).glob('*'):
  if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name):runtime[driver]=dict(device=p.name,state=(p/'power/runtime_status').read_text().strip())
assert len(runtime)==5 and all(r['state']=='suspended' for r in runtime.values())
for name in ['ac4a000.cci','ac4b000.cci','acb3000.camss']:assert Path('/sys/bus/platform/devices',name,'power/runtime_status').read_text().strip()=='suspended'
rails={}
for p in Path('/sys/class/regulator').glob('regulator.*'):
 name=(p/'name').read_text().strip()
 if name.startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-')):rails[name]={k:(p/k).read_text().strip() for k in ['state','num_users']}
assert len(rails)==9 and all(r['state']=='disabled' and r['num_users']=='0' for r in rails.values())
text=subprocess.check_output(['dmesg']);faults={k:text.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp_fatal=b'fatal error received').items()}
assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert not any('/run/k298-oem-tuning' in l for l in Path('/proc/mounts').read_text().splitlines())
print(json.dumps(dict(stage=299,kernel_build=298,release=os.uname().release,runtime=runtime,rails=rails,faults=faults,taint=0,pstore_files=len(list(Path('/sys/fs/pstore').glob('*'))),old_vendor_mounts_absent=True,read_only=True)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25)
(HERE/'baseline-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
