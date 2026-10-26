from pathlib import Path
import hashlib,json,shlex,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;new=storage.candidate();base=new.parent/'libcamera362-serialized-built';old=new.parent/'libcamera387-ipe-built'
assert not new.exists();stat=new.parent.stat();free=__import__('os').statvfs(new.parent).f_bavail*__import__('os').statvfs(new.parent).f_frsize
tree=old/'src/libcamera-v0.7.2';baseline=base/'src/libcamera-v0.7.2'
for leaf in ['camss_ipe.h','camss_ipe.cpp']:assert (tree/'src/libcamera/pipeline/camss-vfe'/leaf).read_bytes()==(HERE.parent/'kernel387'/leaf).read_bytes()
for relative in ['src/ipa/camss-vfe/camss.cpp','src/libcamera/pipeline_handler.cpp','src/libcamera/base/event_dispatcher_poll.cpp']:
 assert (tree/relative).read_bytes()==(baseline/relative).read_bytes()
assert hashlib.sha256((P.parent/'kernel388/libcamera.so.0.7.2').read_bytes()).hexdigest()=='60181b3cd025febfeb1812996bc63aaa53721a47ba45bd6ef1d3f92596329c3d'
code=r'''from pathlib import Path
import json,subprocess
dev=Path('/sys/bus/platform/devices/ac10000.icp');s=json.loads((dev/'state').read_text());m=json.loads((dev/'m2m_status').read_text())
assert (dev/'driver').resolve().name=='qcom-sm8150-icp' and not any(s[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','mapped_bytes','ipe_dma_pending','imported_buffers'])
assert not any(m[k] for k in ['users','running','fatal','pinned','orphans','failed']) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
names={'libcamera','libcamera-ipa','libcamera-tools','libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'};versions={}
for b in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 f=dict(line.split(':',1) for line in b.splitlines() if ':' in line)
 if f.get('P') in names:versions[f['P']]=f['V']
assert len(versions)==7 and all(v==('99990.7.2-r29' if n.startswith('libcamera') else '0.1.0-r24') for n,v in versions.items())
print(json.dumps(dict(packages=versions,normal_icp_idle=True,m2m=m,repository=Path('/etc/apk/repositories.d/60-samurai-camera.list').read_text(),private_defaults={p.name:__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in Path('/etc/libcamera/ipa/camss-vfe').glob('*.yaml')})))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);d=json.loads(q.stdout);(P/'initial-device-private.json').write_bytes(q.stdout)
report=dict(stage=391,base_r29_source=str(baseline),validated_ipe_source=str(tree),candidate_target=str(new),free_ext4_bytes=free,dispatcher_and_ipa_unchanged=True,packages=d['packages'],normal390_platform_idle=True,new_source_not_created_yet=True,passed=True)
(HERE/'initial-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
