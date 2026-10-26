"""Build only the private libcamera core target for the completion fix."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,time
import storage
HERE=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel461')
volume=storage.mount.mounted_build().parent;tree=storage.candidate()/'src/libcamera-v0.7.2'
state=json.loads((HERE/'source-state.json').read_text())
old_state=json.loads((HERE.parent/'kernel452/source-state.json').read_text())
baseline=volume/'libcamera452-full-ownership/src/libcamera-v0.7.2'
proof=json.loads((HERE.parent/'kernel452/build-validation.json').read_text())
assert proof['passed'] and state['completion_ownership_fix']
paths={'libcamera.so.0.7.2':'output/src/libcamera/libcamera.so.0.7.2',
       'ipa_camss_vfe.so':'output/src/ipa/camss-vfe/ipa_camss_vfe.so',
       'ipa_camss_vfe.so.sign':'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign',
       'camss_ipa_proxy':'output/src/libcamera/proxy/worker/camss_ipa_proxy'}
expected={row['name']:row['sha256'] for row in proof['runtime_files']}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check_sources():
 for row in state['source_hashes']:assert sha(tree/row['path'])==row['sha256'],row['path']
 for row in old_state['source_hashes']:assert sha(baseline/row['path'])==row['sha256'],row['path']
 for name,relative in paths.items():assert sha(baseline/relative)==expected[name]
check_sources()
assert not (HERE/'build-validation.json').exists(),'Keep completed builds; do not replay'
assert shutil.disk_usage(volume).free>2*1024**3+128*1024**2
for name,relative in paths.items():assert sha(tree/relative)==expected[name]
version=tree/'output/src/libcamera/version.cpp';version_before=sha(version)
target=['ninja','-C','/work/libcamera/src/libcamera-v0.7.2/output','-j2','src/libcamera/libcamera.so.0.7.2']
start=time.monotonic()
with storage.sdk_candidate():
 plan=subprocess.run(['chroot',str(storage.SDK),*target[:3],'-n',*target[3:]],capture_output=True)
 log=plan.stdout+plan.stderr;(PRIVATE/'core-plan-private.log').write_bytes(log)
 steps=[line for line in log.decode().splitlines() if re.match(r'^\[\d+/\d+\]',line)]
 allowed=['Compiling C++ object src/libcamera/libcamera.so.0.7.2.p/pipeline_camss-vfe_camss_vfe.cpp.o',
          'Generating src/libcamera/version.cpp with a custom command',
          'Compiling C++ object src/libcamera/libcamera.so.0.7.2.p/meson-generated_.._version.cpp.o',
          'Linking target src/libcamera/libcamera.so.0.7.2']
 assert plan.returncode==0 and len(steps) in (2,4) and all(any(label in step for label in allowed) for step in steps),log.decode()
 assert any(allowed[0] in step for step in steps) and any(allowed[-1] in step for step in steps)
 print(json.dumps(dict(stage=461,build_started=True,planned_steps=steps)),flush=True)
 run=subprocess.run(['chroot',str(storage.SDK),*target],capture_output=True)
 (PRIVATE/'core-build-private.log').write_bytes(run.stdout+run.stderr)
unmounted=subprocess.run(['mountpoint','-q',str(storage.SDK/'work/libcamera')],capture_output=True).returncode!=0
report=dict(stage=461,exit_code=run.returncode,seconds=round(time.monotonic()-start,3),planned_steps=steps,
 executed_steps=[line for line in (run.stdout+run.stderr).decode().splitlines() if re.match(r'^\[\d+/\d+\]',line)],
 sdk_bind_unmounted=unmounted,requested_only_core_target=True,private_ipa_version=6,
 completion_ownership_fix=True,drop_root_cause_fixed=False,phone_accessed=False,installed=False,passed=False)
(HERE/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
assert run.returncode==0 and unmounted,(run.stdout+run.stderr).decode()[-4000:]
check_sources();assert sha(version)==version_before,'Generated version changed'
files=[]
for name,relative in paths.items():
 path=tree/relative;digest=sha(path)
 if name=='libcamera.so.0.7.2':
  assert digest!=expected[name];shutil.copyfile(path,PRIVATE/name)
 else:assert digest==expected[name],name+' unexpectedly changed'
 files.append(dict(name=name,bytes=path.stat().st_size,sha256=digest))
report.update(runtime_files=files,baseline452_preserved=True,ipa_proxy_signature_preserved=True,
 source_inputs_unchanged_during_build=True,generated_version_preserved=True,passed=True)
(HERE/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
state.update(build_pending=False,diagnostic_only=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
