"""Recheck the actual phone and preserve a fresh baseline before DT/module deployment."""
from pathlib import Path
import hashlib,json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
release=os.uname().release;tree=Path('/usr/lib/modules')/release
mods={}
for name in ['qcom_pm8008','qcom_pm8008_regulator','imx319','imx471','qcom_camss','v4l2_cci','s5k3m5']:
 q=subprocess.run(['modinfo','-n',name],capture_output=True,text=True)
 path=Path(q.stdout.strip());present=q.returncode==0 and path.is_file()
 mods[name]=dict(file=str(path) if present else None,sha256=sha(path) if present else None,loaded=Path('/sys/module',name).exists())
 if present:
  mods[name]['vermagic']=subprocess.check_output(['modinfo','-F','vermagic',str(path)],text=True).strip()
  mods[name]['intree']=subprocess.check_output(['modinfo','-F','intree',str(path)],text=True).strip()
kernel=subprocess.check_output(['dmesg'])
processes=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name in ['snapshot','megapixels','cam','gst-launch-1.0']:processes.append(dict(pid=int(p.name),comm=name))
 except OSError:pass
boot=next(p for p in Path('/dev/disk/by-partlabel').iterdir() if p.name=='boot')
report=dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),release=release,kernel_version=os.uname().version,
 boot_partition_sha256=sha(boot),module_count=len(list(tree.rglob('*.ko'))),modules=mods,
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),camera_clients=processes,
 faults={k:kernel.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()},
 runtime={n:Path('/sys/bus/i2c/devices',n,'power/runtime_status').read_text().strip() for n in ['7-0010','9-0010']},
 kernel_log=kernel.decode(errors='replace'),package_db_sha256=sha('/lib/apk/db/installed'))
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=35)
(host.PRIVATE/'deployment-baseline-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
proof=json.loads((R/'build-package-validation.json').read_text())
assert d['boot_partition_sha256']==proof['rollback_boot_sha256'] and d['kernel_version'].startswith('#183 ')
assert d['taint']==0 and not any(d['faults'].values()) and not d['camera_clients']
assert all(v=='suspended' for v in d['runtime'].values())
old=json.loads((host.PRIVATE/'current-inspection-private.json').read_text())
for name in old['modules']:assert d['modules'][name]['sha256']==old['modules'][name]['sha256']
assert d['modules']['v4l2_cci']['intree']=='Y'
build=json.loads((R/'current-module-build-validation.json').read_text())
assert d['modules']['v4l2_cci']['vermagic']==build['vermagic']
summary=dict(stage=270,current_boot_and_image183_verified=True,current_boot267_hash_verified=True,
 existing_camera_module_hashes_preserved=True,v4l2_cci_present=True,
 cci_existing_matches_rebuilt=d['modules']['v4l2_cci']['sha256']==build['modules']['v4l2-cci.ko']['sha256'],
 telephoto_module_already_present=d['modules']['s5k3m5']['file'] is not None,
 no_camera_clients=True,taint=0,faults=d['faults'],module_count=d['module_count'],ready_for_staging=True)
(R/'deployment-preflight-validation.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
