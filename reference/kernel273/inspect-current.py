"""Current-boot baseline for the new main-camera deployment; no phone mutation."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
release=os.uname().release;tree=Path('/usr/lib/modules')/release
mods={}
for name in ['qcom_pm8008','qcom_pm8008_regulator','imx319','imx471','qcom_camss','v4l2_cci','s5k3m5']:
 p=Path(subprocess.check_output(['modinfo','-n',name],text=True).strip())
 mods[name]=dict(path=str(p),sha256=sha(p),loaded=Path('/sys/module',name).exists(),vermagic=subprocess.check_output(['modinfo','-F','vermagic',str(p)],text=True).strip())
old=Path('/var/lib/samurai/k271-gain-candidates')
assert (old/'forward-manifest.json').is_file() and (old/'forward/packages.adb').is_file()
runtime={}
for bus,names in [('i2c',['7-0010','8-002d','9-0010']),('platform',['ac4a000.cci','ac4b000.cci','acb3000.camss'])]:
 for name in names:runtime[name]=Path('/sys/bus',bus,'devices',name,'power/runtime_status').read_text().strip()
kernel=subprocess.check_output(['dmesg']);clients=[]
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name in ['snapshot','megapixels','cam','gst-launch-1.0']:clients.append(dict(pid=int(p.name),comm=name))
 except OSError:pass
boot=Path(subprocess.check_output(['findfs','PARTLABEL=boot'],text=True).strip())
report=dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),release=release,kernel_version=os.uname().version,
 boot_partition_sha256=sha(boot),module_count=len(list(tree.rglob('*.ko'))),modules=mods,runtime=runtime,
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),camera_clients=clients,
 faults={k:kernel.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',fatal=b'fatal error received',modem=b'crash detected in modem').items()},
 package_db_sha256=sha('/lib/apk/db/installed'),old_repo=str(old),package_count=len(subprocess.check_output(['apk','info']).splitlines()),
 packages={name:subprocess.check_output(['apk','info','-v',name],text=True).strip().splitlines() for name in ['libcamera','libcamera-ipa','samurai-camera-config','samurai-camera-stack']},
 pstore={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in Path('/sys/fs/pstore').glob('*') if p.is_file()})
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=40);(host.PRIVATE/'deployment-baseline-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
assert d['boot_partition_sha256']=='0904b3b6616652e08709891cfdee34f1f733ff1e7022b7749bedea758108e4e8'
assert d['kernel_version'].startswith('#183 ') and d['module_count']==774 and d['package_count']==961
assert d['taint']==0 and not any(d['faults'].values()) and not d['camera_clients'] and all(x=='suspended' for x in d['runtime'].values())
lock=json.loads((R.parents[1]/'linux-port/camera/deployment-lock.json').read_text())
for name,item in d['modules'].items():
 key={'qcom_pm8008':'qcom-pm8008','qcom_pm8008_regulator':'qcom-pm8008-regulator','qcom_camss':'qcom-camss','v4l2_cci':'v4l2-cci'}.get(name,name)
 # The product lock uses module file names; resolve either historical spelling.
 choices=[v for n,v in lock['kernel_modules'].items() if n.replace('-','_').removesuffix('.ko')==name]
 assert len(choices)==1 and item['sha256']==choices[0]['sha256'] and item['loaded'],name
report=dict(stage=273,current_boot270_image183_verified=True,seven_camera_module_hashes_match_deployment_lock=True,module_count=774,
 existing_r20_signed_repo_present=True,no_camera_clients=True,camera_resources_suspended=True,taint=0,faults=d['faults'],
 package_count=961,phone_unchanged=True)
(R/'deployment-preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
