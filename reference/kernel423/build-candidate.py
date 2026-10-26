from pathlib import Path
import hashlib,json,shutil,subprocess,time,sys
import storage
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel423');P.mkdir(mode=0o700,exist_ok=True)
assert json.loads((HERE/'source-state.json').read_text())['source_prepared']
tree=storage.candidate()/'src/libcamera-v0.7.2'
for name in ['ipe_tone_profile.h','ipe_tone_profile.cpp']:
    shutil.copyfile(HERE/name,tree/'src/ipa/camss-vfe'/name)
if '--rebuild-callers' in sys.argv:
    # A failed earlier build overlapped source preparation. Touch every changed
    # input so Ninja cannot accept objects compiled before that preparation.
    for name in ['src/ipa/camss-vfe/camss.cpp','src/ipa/camss-vfe/ipe_tone_profile.cpp',
        'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp','include/libcamera/ipa/camss.mojom']:
        (tree/name).touch()
attempt=1
while (P/('candidate-build-r'+str(attempt)+'.log')).exists():attempt+=1
start=time.monotonic()
with storage.sdk_candidate():
    q=subprocess.run(['chroot',str(storage.SDK),'ninja','-C','/work/libcamera/src/libcamera-v0.7.2/output','-j4'],capture_output=True)
(P/('candidate-build-r'+str(attempt)+'.log')).write_bytes(q.stdout+q.stderr)
r=dict(stage=423,attempt=attempt,exit_code=q.returncode,seconds=round(time.monotonic()-start,2),
    callers_forced_recompiled='--rebuild-callers' in sys.argv,
    private_ipa_version=3,automatic_numeric_caller_compiled=not q.returncode,installed=False,sdk_bind_unmounted=True,passed=not q.returncode)
for n in ['build-validation.json','build-r'+str(attempt)+'-validation.json']:(HERE/n).write_text(json.dumps(r,indent=2)+'\n')
print((q.stdout+q.stderr).decode()[-4500:]);print(json.dumps(r),flush=True);assert not q.returncode
files={'libcamera.so.0.7.2':'output/src/libcamera/libcamera.so.0.7.2',
    'ipa_camss_vfe.so':'output/src/ipa/camss-vfe/ipa_camss_vfe.so','ipa_camss_vfe.so.sign':'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign',
    'camss_ipa_proxy':'output/src/libcamera/proxy/worker/camss_ipa_proxy'}
rows=[]
for name,rel in files.items():
    source=tree/rel;shutil.copyfile(source,P/name);rows.append(dict(name=name,bytes=source.stat().st_size,sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
r['runtime_files']=rows
for n in ['build-validation.json','build-r'+str(attempt)+'-validation.json']:(HERE/n).write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(rows,indent=2))
