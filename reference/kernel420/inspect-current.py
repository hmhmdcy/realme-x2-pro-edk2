"""Inspect the actual build environment and formal camera stack before release."""
from pathlib import Path
import json,shlex,subprocess
import host,storage
HERE=Path(__file__).resolve().parent
build=storage.mount.mounted_build();space=__import__('shutil').disk_usage(build)
markers=[]
for stage in [391,418,419]:
 p=host.PRIVATE.parent/f'kernel{stage}'
 for n in ['package-build-state.json','intree-build-state.json']:
  file=p/n
  if file.exists():
   s=json.loads(file.read_text());pid=s.get('pid');live=Path('/proc',str(pid)).exists()
   markers.append(dict(stage=stage,name=n,terminal=s.get('terminal'),pid_currently_exists=live))
   assert s.get('terminal') or not live,(file,s)
q=host.ssh('python3 -c '+shlex.quote(r'''from pathlib import Path
import json,subprocess
dev=Path('/sys/bus/platform/devices/ac10000.icp')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
names={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'};versions={}
for b in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 f=dict(line.split(':',1) for line in b.splitlines() if ':' in line)
 if f.get('P') in names:versions[f['P']]=f['V']
assert len(versions)==7
print(json.dumps(dict(m2m=json.loads((dev/'m2m_status').read_text()),core=json.loads((dev/'state').read_text()),taint=int(Path('/proc/sys/kernel/tainted').read_text()),packages=versions,boot_guard394_matches=True,private_defaults={p.name:__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in Path('/etc/libcamera/ipa/camss-vfe').glob('*.yaml')})))
'''),timeout=25)
(host.PRIVATE/'initial-device-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
assert not any(d['m2m'][k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
assert not any(d['core'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','ipe_dma_pending','request_fw_mapped','imported_buffers','cleanup_error','pc_error'])
assert d['taint']==512 and all(v==('99990.7.2-r30' if n.startswith('libcamera') else '0.1.0-r25') for n,v in d['packages'].items())
r=dict(stage=420,free_build_bytes=space.free,build_markers=markers,formal_versions_r30_r25=True,boot_guard394_matches=True,taint=512,device_idle_resources_released=True,installed=False,passed=True)
(HERE/'initial-state-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
