from pathlib import Path
import ast,hashlib,io,json,re,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert run in ['r1','r2']
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':390")
body=(HERE/'runtime-worker-body.py').read_text()
if run=='r2':
 body=body.replace("['users','running','jobs','pinned','orphans']", "['users','running','pinned','orphans']",1)
 a=body.index(" with (root/'export-client.log')");b=body.index(" lib=root/'lib'",a)
 body=body[:a]+''' previous_root=Path('/var/lib/samurai/k390-runtime-r1')
 previous=json.loads((previous_root/'state.json').read_text())
 assert previous['terminal'] and previous['export_lifetime_passed'] and previous['native_status']['completed']==18
 proc=Path('/proc',str(previous['pid']))
 assert not proc.exists() or (proc/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z' or str(previous_root/'worker.py').encode() not in (proc/'cmdline').read_bytes()
 native_status=previous['native_status'];native_state=previous['native_core_state']
 assert before['jobs']==before['completed']==before['direct_completed']==native_status['completed']==18 and before['failed']==before['cancelled']==0
 state.update(native_evidence_root=str(previous_root),native_report=previous['native_report'],native_status=native_status,native_core_state=native_state,export_lifetime_passed=True,export_evidence_reused=True,initial_status=before)
 save('prior-native-evidence-checked')
'''+body[b:]
source=prefix+'\n'+body;ast.parse(source);worker=P/('runtime-worker-'+run+'.py');worker.write_text(source)
s=(HERE.parent/'kernel388/camera-client.py').read_text().replace("'stage':388","'stage':390").replace('stage=388','stage=390')
s=s.replace('/var/lib/samurai/k378-recovered/boot-id-private.txt','/var/lib/samurai/k390-active/boot-id-private.txt')
s=s.replace('/sys/bus/platform/devices/ac10000.samurai-icp356-boot/m2m_status','/sys/bus/platform/devices/ac10000.icp/m2m_status')
s=s.replace('/sys/module/camss_icp_a5_boot_test/parameters/result','/sys/bus/platform/devices/ac10000.icp/state')
s=s.replace("root/'snapshot-collector.py'","root/'dump-collector.py'")
s=s.replace('items=services();wait_idle();stopped=True;stop_services(items);wait_idle()',"wait_idle();assert not any(processes(n) for n in ['pipewire','wireplumber'])")
s=s.replace("  if stopped:restart(items,'restore',started)\n  wait_idle();restored=all(len(processes(name))==1 for name in ['pipewire','wireplumber'])", "  wait_idle();restored=not any(processes(name) for name in ['pipewire','wireplumber'])")
s=s.replace('services_restored=restored','services_kept_stopped_for_outer=restored');ast.parse(s);(HERE/'camera-client.py').write_text(s)
files={'worker.py':worker,'camera-client.py':HERE/'camera-client.py','dump-collector.py':HERE/'dump-collector.py'}
cached={}
for name,path,remote in [('m2m-client',P.parent/'kernel386/m2m-client','/var/lib/samurai/k388-framework-r1/native/m2m-client'),('export-lifetime-client',P.parent/'kernel388/export-lifetime-client','/var/lib/samurai/k388-framework-r1/native/export-lifetime-client'),('pipeline-fixture',P.parent/'kernel363/pipeline-fixture','/var/lib/samurai/k387-pipeline-r5/pipeline-fixture'),('pipeline-smoke',P.parent/'kernel388/pipeline-smoke','/var/lib/samurai/k387-pipeline-r5/pipeline-smoke'),('libcamera.so.0.7.2',P.parent/'kernel388/libcamera.so.0.7.2','/var/lib/samurai/k387-pipeline-r5/libcamera.so.0.7.2')]:
 if name=='m2m-client':path=Path(json.loads((HERE.parent/'kernel386/client-build-validation.json').read_text())['private_path'])
 cached[name]=dict(path=remote,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
manifest=dict(sha256={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()}|{n:r['sha256'] for n,r in cached.items()})
payload=io.BytesIO()
with tarfile.open(fileobj=payload,mode='w:gz') as tar:
 for n,p in files.items():tar.add(p,arcname=n)
 data=json.dumps(manifest).encode();m=tarfile.TarInfo('manifest.json');m.size=len(data);tar.addfile(m,io.BytesIO(data))
code=r'''from pathlib import Path
import hashlib,io,json,os,shutil,sys,tarfile
root=Path(RUNTIME_ROOT);assert not root.exists();cached=CACHED
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k390-active/boot-id-private.txt').read_bytes()
for n,r in cached.items():assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256']
tar=tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz');members=tar.getmembers();assert {m.name for m in members}==NAMES and all(m.isfile() for m in members)
root.mkdir(mode=0o700)
for m in members:
 with (root/m.name).open('xb') as f:f.write(tar.extractfile(m).read());f.flush();os.fsync(f.fileno())
for n,r in cached.items():(root/n).symlink_to(r['path'])
for n,digest in json.loads((root/'manifest.json').read_text())['sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==digest
print(json.dumps(dict(staged=True,root=str(root),passed=True)))
'''.replace('RUNTIME_ROOT',repr('/var/lib/samurai/k390-runtime-'+run)).replace('CACHED',repr(cached)).replace('NAMES',repr(set(files)|{'manifest.json'}))
q=host.ssh('python3 -c '+shlex.quote(code),input=payload.getvalue(),timeout=25);(HERE/'runtime-staging-validation.json').write_bytes(q.stdout);print(q.stdout.decode())
