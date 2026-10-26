"""Observe the new boot's normal user services without replacing or restarting them."""
from pathlib import Path
import json
import host

R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import json,os
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k267-work/boot-id-private.txt').read_bytes()
rows=[]
for name in ['pipewire','wireplumber']:
 found=[]
 for p in Path('/proc').glob('[0-9]*'):
  try:
   if (p/'comm').read_text().strip()==name and int((p/'status').read_text().split('Uid:',1)[1].split()[0])==10000:found.append(p)
  except OSError:pass
 assert len(found)==1,(name,len(found));p=found[0]
 maps=(p/'maps').read_text();assert '/usr/lib/libpipewire-0.3.so.0.1609.0' in maps
 assert not any('/var/lib/samurai/k' in line and '.so' in line for line in maps.splitlines())
 if name=='wireplumber':assert '/usr/lib/spa-0.2/libcamera/libspa-libcamera.so' in maps
 env={k.decode():v.decode() for item in (p/'environ').read_bytes().split(b'\0') if b'=' in item for k,v in [item.split(b'=',1)]}
 assert not any(k in env for k in ['LD_LIBRARY_PATH','SPA_PLUGIN_DIR','PIPEWIRE_MODULE_DIR'])
 rows.append(dict(name=name,pid=int(p.name),start_ticks=(p/'stat').read_text().rsplit(')',1)[1].split()[19]))
report=dict(stage=267,new_processes=rows,spa_path='/usr/lib/spa-0.2/libcamera/libspa-libcamera.so',spa_candidate_active=False,
 original_session_services=True,normal_system_library_paths=True)
(r/'k267-services-current-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'services-current-private.json').write_bytes(q.stdout)
(R/'services-current-validation.json').write_text(json.dumps(json.loads(q.stdout),indent=2)+'\n')
print(q.stdout.decode())
