"""Build the matching private IPA2, generated proxy and camera library."""
from pathlib import Path
import hashlib,json,shutil,subprocess,time
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'history-validation.json').read_text())['passed']
if json.loads((HERE/'source-state.json').read_text()).get('statistics_published_before_ipa_parameter_call'):
 assert json.loads((HERE/'statistics-reentry-validation.json').read_text())['passed']
attempt=1
while (P/('candidate-build-r'+str(attempt)+'.log')).exists():attempt+=1
start=time.monotonic()
with storage.sdk_candidate():
 q=subprocess.run(['chroot',str(storage.SDK),'ninja','-C','/work/libcamera/src/libcamera-v0.7.2/output','-j4'],capture_output=True)
(P/('candidate-build-r'+str(attempt)+'.log')).write_bytes(q.stdout+q.stderr)
r=dict(stage=421,attempt=attempt,exit_code=q.returncode,seconds=round(time.monotonic()-start,2),private_ipa_version=2,generated_proxy_and_library_built=not q.returncode,installed=False,passed=not q.returncode)
(HERE/'build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print((q.stdout+q.stderr).decode()[-2000:]);print(json.dumps(r));assert not q.returncode
tree=storage.candidate()/'src/libcamera-v0.7.2';files={
 'libcamera.so.0.7.2':'output/src/libcamera/libcamera.so.0.7.2',
 'ipa_camss_vfe.so':'output/src/ipa/camss-vfe/ipa_camss_vfe.so',
 'ipa_camss_vfe.so.sign':'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign',
 'camss_ipa_proxy':'output/src/libcamera/proxy/worker/camss_ipa_proxy'}
rows=[]
for name,relative in files.items():
 source=tree/relative;assert source.is_file(),source;shutil.copyfile(source,P/name);rows.append(dict(name=name,bytes=source.stat().st_size,sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
r.update(runtime_files=rows)
for n in ['build-validation.json','build-r'+str(attempt)+'-validation.json']:(HERE/n).write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(rows,indent=2))
