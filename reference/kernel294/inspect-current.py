from pathlib import Path
import hashlib,json
import host
ROOT=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,re,subprocess
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k293+' and os.uname().version.startswith('#293 ')
target=Path('/usr/lib/modules')/os.uname().release
inventory=json.loads(Path('/var/lib/samurai/k293-deployment/module-inventory-private.json').read_text())
assert inventory=={str(p.relative_to(target)):hashlib.sha256(p.read_bytes()).hexdigest() for p in target.rglob('*.ko')} and len(inventory)==778
sensors={}
for name in ['s5kgw1','imx471','imx319','s5k3m5','lc898219xi']:
 p=next(p for p in Path('/sys/bus/i2c/drivers',name).glob('*') if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name));sensors[name]=dict(device=p.name,state=(p/'power/runtime_status').read_text().strip())
assert all(s['state']=='suspended' for s in sensors.values())
kernel=subprocess.check_output(['dmesg']);faults={k:kernel.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp=b'fatal error received').items()}
assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
ssc=json.loads(Path('/run/samurai-ssc/state.json').read_text())
procs=[]
for name in ['phoc','phosh','pipewire','wireplumber']:
 pid=int(subprocess.check_output(['pgrep','-x',name],text=True));f=Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split();assert f[0]!='Z';procs.append(dict(comm=name,pid=pid,start_ticks=f[19]))
print(json.dumps(dict(stage=294,kernel_build=293,release=os.uname().release,module_count=778,all_modules_verified=True,sensors=sensors,faults=faults,taint=0,
 processes=procs,ssc_started=ssc['started'],ssc_failure=ssc.get('readiness_failure'),pstore_files=len(list(Path('/sys/fs/pstore').glob('*'))))))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25);(host.PRIVATE/'preflight-private.json').write_bytes(q.stdout)
report=json.loads(q.stdout);(ROOT/'runtime-preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
