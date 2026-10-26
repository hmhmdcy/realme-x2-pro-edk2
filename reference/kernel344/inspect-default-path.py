from pathlib import Path
import importlib.util,json,shlex
import host

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage342',HERE.parent/'kernel342/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
tree=storage.candidate()/'src/libcamera-v0.7.2'
source=(tree/'src/libcamera/ipa_proxy.cpp').read_text();build=(tree/'output/config.h').read_text()
definitions=[line for line in build.splitlines() if any(key in line for key in ['IPA_CONFIG_DIR','LIBCAMERA_SYSCONF_DIR','LIBCAMERA_DATA_DIR'])]
assert any('"/etc/libcamera/ipa:/usr/share/libcamera/ipa"' in line for line in definitions),definitions
code='''
from pathlib import Path
import json
result={}
for name in ['pipewire','wireplumber']:
 rows=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()==name and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':
    env=dict(x.decode().split('=',1) for x in (p/'environ').read_bytes().split(b'\\0') if x)
    rows.append(dict(pid=int(p.name),uid=p.stat().st_uid,libcamera_env={k:v for k,v in env.items() if k.startswith('LIBCAMERA_')}))
  except (FileNotFoundError,ProcessLookupError):pass
 result[name]=rows
config=Path('/etc/libcamera/ipa/camss-vfe');existing={}
for model in ['s5kgw1','imx471','imx319','s5k3m5']:
 p=config/(model+'.yaml');existing[model]=dict(exists=p.exists(),is_symlink=p.is_symlink())
print(json.dumps(dict(services=result,existing_private_profiles=existing,taint=int(Path('/proc/sys/kernel/tainted').read_text()),
 runtime={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']})))
'''
data=json.loads(host.raw_ssh('python3 -c '+shlex.quote(code),timeout=25).stdout)
(host.PRIVATE/'default-path-state-private.json').write_text(json.dumps(data,indent=2)+'\n')
report=dict(stage=344,compiled_configuration_definitions=definitions,etc_before_packaged_data=True,
 existing_private_profiles=data['existing_private_profiles'],service_libcamera_environment=data['services'],runtime=data['runtime'],taint=data['taint'],phone_changed=False)
(HERE/'configuration-path-observation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
