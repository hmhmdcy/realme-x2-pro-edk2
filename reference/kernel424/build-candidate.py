from pathlib import Path
import hashlib,json,shutil,subprocess,time
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;state=json.loads((HERE/'source-state.json').read_text());assert state['source_prepared']
tree=storage.candidate()/'src/libcamera-v0.7.2'
def unchanged():
 for row in state['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
unchanged();attempt=1
while (P/('candidate-build-r'+str(attempt)+'.log')).exists():attempt+=1
start=time.monotonic()
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'ninja','-C','/work/libcamera/src/libcamera-v0.7.2/output','-j4'],capture_output=True)
unchanged();log=q.stdout+q.stderr;(P/('candidate-build-r'+str(attempt)+'.log')).write_bytes(log)
r=dict(stage=424,attempt=attempt,exit_code=q.returncode,seconds=round(time.monotonic()-start,2),source_inputs_unchanged_during_build=True,
 private_ipa_version=3,core_and_kernel_interface_unchanged=True,sdk_bind_unmounted=True,installed=False,passed=not q.returncode)
for n in ['build-validation.json','build-r'+str(attempt)+'-validation.json']:(HERE/n).write_text(json.dumps(r,indent=2)+'\n')
print(log.decode()[-4000:]);assert not q.returncode
assert b'camss.cpp.o' in log and b'ipe_tone_profile.cpp.o' in log
files={'libcamera.so.0.7.2':'output/src/libcamera/libcamera.so.0.7.2','ipa_camss_vfe.so':'output/src/ipa/camss-vfe/ipa_camss_vfe.so',
 'ipa_camss_vfe.so.sign':'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign','camss_ipa_proxy':'output/src/libcamera/proxy/worker/camss_ipa_proxy'}
rows=[]
for n,rel in files.items():
 p=tree/rel;shutil.copyfile(p,P/n);rows.append(dict(name=n,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
prior={x['name']:x['sha256'] for x in json.loads((HERE.parent/'kernel423/build-validation.json').read_text())['runtime_files']}
assert all(x['sha256']==prior[x['name']] for x in rows if x['name'] in ['libcamera.so.0.7.2','camss_ipa_proxy'])
r.update(runtime_files=rows,actual_changed_ipa_sources_recompiled=True,core_proxy_identical_to_validated423=True)
for n in ['build-validation.json','build-r'+str(attempt)+'-validation.json']:(HERE/n).write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
