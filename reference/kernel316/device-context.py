import json,shlex
import host
code='''
from pathlib import Path
import json,os,subprocess
models=['s5kgw1','imx471','imx319','s5k3m5'];sensors={}
for model in models:
 for p in Path('/sys/bus/i2c/drivers',model).iterdir():
  if (p/'of_node').exists():sensors[model]='/base'+str((p/'of_node').resolve()).split('/base',1)[1]
repo=Path('/etc/apk/repositories.d/60-samurai-camera.list').read_text()
locations=[]
for line in repo.splitlines():
 line=line.strip()
 if not line or line.startswith('#'):continue
 if line.startswith('@'):line=line.split(None,1)[1]
 locations.append(line if line.startswith(('/','file:///')) else 'nonlocal repository')
packages={}
for block in Path('/lib/apk/db/installed').read_text().split('\\n\\n'):
 fields=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
 if fields.get('P') in ['libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack']:packages[fields['P']]=fields['V']
consumers={}
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name in ['pipewire','wireplumber']:
   env=dict(x.decode().split('=',1) for x in (p/'environ').read_bytes().split(b'\\0') if x)
   consumers[name]={'pid':int(p.name),'uid':p.stat().st_uid,'camera_environment':{k:v for k,v in env.items() if k in ['LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_SOFTISP_USE_GPU','LIBCAMERA_IPA_FORCE_ISOLATION']}}
 except FileNotFoundError:pass
print(json.dumps({'release':os.uname().release,'packages':packages,
 'repository':locations,
 'sensors':sensors,'consumers':consumers,'camss':Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip()}))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20)
(host.PRIVATE/'device-context.json').write_bytes(q.stdout);print(q.stdout.decode())
