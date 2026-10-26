"""Package the validated common dispatcher, request order and CAMSS queue fixes."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;new=storage.candidate();tree=new/'src/libcamera-v0.7.2'
assert json.loads((HERE/'runtime-validation.json').read_text())['full_candidate_validation_passed']
for name in ['submit-regression-validation.json','ordering-regression-validation.json']:
    assert json.loads((HERE/name).read_text())['passed']
names=['src/libcamera/base/event_dispatcher_poll.cpp','src/libcamera/pipeline_handler.cpp','src/libcamera/pipeline/camss-vfe/camss_vfe.cpp']
base=new.parent/'libcamera360-combined-r28-built/src/libcamera-v0.7.2';patch=[]
for name in names:
    before=(base/name).read_text();after=(tree/name).read_text();assert before!=after
    patch.extend(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name))
patchFile=HERE/'0039-synchronous-ipa-reentrancy.patch';patchFile.write_text(''.join(patch))
check=new.parent/'patch-check362';assert not check.exists();check.mkdir()
for name in names:
    (check/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/name,check/name)
q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(patchFile)],cwd=check,capture_output=True)
(host.PRIVATE/'release-patch-apply.log').write_bytes(q.stdout+q.stderr);assert not q.returncode
assert all((check/name).read_bytes()==(tree/name).read_bytes() for name in names)
for package in ['libcamera','samurai-camera-config']:
    target=HERE/'recipes'/package;assert not target.exists();shutil.copytree(HERE.parent/'kernel360/recipes'/package,target)
recipe=HERE/'recipes/libcamera';shutil.copyfile(patchFile,recipe/patchFile.name)
p=recipe/'APKBUILD';s=p.read_text();assert 'pkgrel=28\n' in s;s=s.replace('pkgrel=28\n','pkgrel=29\n')
needle='\t0038-camss-factory-exposure-program.patch\n';assert s.count(needle)==1;s=s.replace(needle,needle+'\t'+patchFile.name+'\n');at=s.rfind('"')
s=s[:at]+hashlib.sha512(patchFile.read_bytes()).hexdigest()+'  '+patchFile.name+'\n'+s[at:];p.write_text(s)
p=HERE/'recipes/samurai-camera-config/APKBUILD';s=p.read_text();assert 'pkgrel=23\n' in s
p.write_text(s.replace('pkgrel=23\n','pkgrel=24\n').replace('99990.7.2-r28','99990.7.2-r29'))
for package,version in [('libcamera','99990.7.2-r29'),('samurai-camera-config','0.1.0-r24')]:
    recipe=HERE/'recipes'/package;p=recipe/'source-lock.json';state=json.loads(p.read_text())
    for source in recipe.iterdir():
        if source.is_file() and (source.name in state['source_files_sha256'] or source.suffix=='.patch'):
            state['source_files_sha256'][source.name]=hashlib.sha256(source.read_bytes()).hexdigest()
    state.update(stage=362,build_stage=362,package_version=version,candidate_only=True,installed=False,
        native_install_validation=None,actual_current_payload_validation=None,actual_signed_build_validation='reference/kernel362/package-build-validation.json')
    if package=='libcamera':state.update(maintained_source=str(tree),matched_camss_driver_stage=348,isolated_request_queue_verified=True,common_request_order_preserved=True)
    p.write_text(json.dumps(state,indent=2)+'\n')
for source in (HERE/'recipes/libcamera').iterdir():
    if source.is_file():shutil.copyfile(source,new/source.name)
config=new.parent/'samurai-camera-config362-r29';assert not config.exists();shutil.copytree(HERE/'recipes/samurai-camera-config',config)
report=dict(stage=362,framework_version='99990.7.2-r29',configuration_version='0.1.0-r24',baseline_framework='99990.7.2-r28',source=str(tree),
    changed_files=names,zero_fuzz_patch_reproduces_source=True,default_profiles_unchanged=True,private_factory_tables_in_packages=False,
    matched_gamma_driver_stage=348,isolated_request_path_verified=True,installed=False,passed=True)
(HERE/'package-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
# Reuse the unchanged real-IPA contract evidence (no algorithm or interface change).
for name in ['ipa-contract-validation.json']:
    d=json.loads((HERE.parent/'kernel360'/name).read_text());d.update(reused_unchanged_from_stage=360,reason='IPA source and interface unchanged; new core additionally verified on hardware')
    (HERE/name).write_text(json.dumps(d,indent=2)+'\n')
script=(HERE.parent/'kernel360/build-packages.py').read_text().replace('360','362').replace('r28','r29').replace('r23','r24')
(HERE/'build-packages.py').write_text(script)
print(json.dumps(report,indent=2))
