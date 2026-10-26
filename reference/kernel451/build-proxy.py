from pathlib import Path
import hashlib,json,shutil,subprocess,time
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build();tree=storage.candidate()/'src/libcamera-v0.7.2'
state=json.loads((HERE/'source-state.json').read_text());assert not state['proxy_optimization_pending']
for row in state['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
base=json.loads((HERE.parent/'kernel450/build-validation.json').read_text());assert base['passed']
paths={'libcamera.so.0.7.2':'output/src/libcamera/libcamera.so.0.7.2','ipa_camss_vfe.so':'output/src/ipa/camss-vfe/ipa_camss_vfe.so','ipa_camss_vfe.so.sign':'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign','camss_ipa_proxy':'output/src/libcamera/proxy/worker/camss_ipa_proxy'}
expected={row['name']:row['sha256'] for row in base['runtime_files']}
for name,relative in paths.items():assert hashlib.sha256((tree/relative).read_bytes()).hexdigest()==expected[name]
assert not (P/'proxy-build.log').exists(),'Inspect a prior build result before another attempt'
start=time.monotonic()
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'ninja','-C','/work/libcamera/src/libcamera-v0.7.2/output','-j4','src/libcamera/proxy/worker/camss_ipa_proxy'],capture_output=True)
(P/'proxy-build.log').write_bytes(q.stdout+q.stderr)
r=dict(stage=451,exit_code=q.returncode,seconds=round(time.monotonic()-start,2),only_proxy_target_requested=True,sdk_bind_unmounted=True,phone_accessed=False,installed=False,build_command_passed=not q.returncode,passed=False)
(HERE/'build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print((q.stdout+q.stderr).decode()[-3000:]);assert not q.returncode
rows=[]
for name,relative in paths.items():
 file=tree/relative;digest=hashlib.sha256(file.read_bytes()).hexdigest()
 if name!='camss_ipa_proxy':assert digest==expected[name],name+' unexpectedly changed'
 else:assert digest!=expected[name];shutil.copyfile(file,P/name)
 rows.append(dict(name=name,bytes=file.stat().st_size,sha256=digest))
for row in state['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
r.update(runtime_files=rows,core450_ipa_signature_unchanged=True,private_ipa_version=6,passed=True)
(HERE/'build-validation.json').write_text(json.dumps(r,indent=2)+'\n');state['build_pending']=False
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(r,indent=2))
