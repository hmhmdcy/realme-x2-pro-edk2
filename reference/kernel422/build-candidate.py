from pathlib import Path
import hashlib,json,shutil,subprocess,time
import storage
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel422')
for name in ['static','frame','numeric-history']:
    assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
attempt=1
while (P/('candidate-build-r'+str(attempt)+'.log')).exists():attempt+=1
start=time.monotonic()
with storage.sdk_candidate():
    q=subprocess.run(['chroot',str(storage.SDK),'ninja','-C','/work/libcamera/src/libcamera-v0.7.2/output','-j4'],capture_output=True)
(P/('candidate-build-r'+str(attempt)+'.log')).write_bytes(q.stdout+q.stderr)
r=dict(stage=422,attempt=attempt,exit_code=q.returncode,seconds=round(time.monotonic()-start,2),
       common_libipa_tmc_ltm_math_integrated=True,private_ipa_version=2,automatic_runtime_generation=False,
       sdk_bind_unmounted=True,installed=False,passed=not q.returncode)
for n in ['build-validation.json','build-r'+str(attempt)+'-validation.json']:(HERE/n).write_text(json.dumps(r,indent=2)+'\n')
print((q.stdout+q.stderr).decode()[-2600:]);print(json.dumps(r),flush=True);assert not q.returncode
tree=storage.candidate()/'src/libcamera-v0.7.2';names={
    'libcamera.so.0.7.2':'output/src/libcamera/libcamera.so.0.7.2',
    'ipa_camss_vfe.so':'output/src/ipa/camss-vfe/ipa_camss_vfe.so',
    'ipa_camss_vfe.so.sign':'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign',
    'camss_ipa_proxy':'output/src/libcamera/proxy/worker/camss_ipa_proxy'}
rows=[]
for name,path in names.items():
    source=tree/path;shutil.copyfile(source,P/name);rows.append(dict(name=name,bytes=source.stat().st_size,sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
r['runtime_files']=rows
for n in ['build-validation.json','build-r'+str(attempt)+'-validation.json']:(HERE/n).write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(rows,indent=2))
