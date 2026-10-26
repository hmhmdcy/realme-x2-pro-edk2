"""Prepare r28/r23 candidates from the tested r27 recipe, preserving defaults."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];new=storage.candidate();tree=new/'src/libcamera-v0.7.2'
gamma=new.parent/'libcamera349-gamma-built/src/libcamera-v0.7.2';base=new.parent/'libcamera342-r27-built/src/libcamera-v0.7.2'
ae=json.loads((HERE.parent/'kernel359/source-state.json').read_text())['changed'];gammaNames=json.loads((HERE.parent/'kernel349/source-state.json').read_text())['changed_sources'];names=sorted(set(ae+gammaNames))
patch=[]
for name in ae:
    old=gamma/name;before=old.read_text() if old.exists() else '';after=(tree/name).read_text();assert before!=after
    patch.extend(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/'+name if old.exists() else '/dev/null',tofile='b/'+name))
newPatch=HERE/'0038-camss-factory-exposure-program.patch';newPatch.write_text(''.join(patch))
gammaPatch=HERE.parent/'kernel349/0037-camss-static-ife-gamma.patch'
check=new.parent/'patch-check360';assert not check.exists();check.mkdir()
for name in names:
    if (base/name).exists():(check/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/name,check/name)
for patchFile in [gammaPatch,newPatch]:
    q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(patchFile)],cwd=check,capture_output=True)
    (host.PRIVATE/(patchFile.stem+'-apply.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(patchFile.name,q.stdout.decode(),q.stderr.decode())
assert all((check/name).read_bytes()==(tree/name).read_bytes() for name in names)
for package in ['libcamera','samurai-camera-config']:
    target=HERE/'recipes'/package;assert not target.exists();shutil.copytree(ROOT/'linux-port/packages'/package,target)
recipe=HERE/'recipes/libcamera'
for patchFile in [gammaPatch,newPatch]:shutil.copyfile(patchFile,recipe/patchFile.name)
p=recipe/'APKBUILD';s=p.read_text();assert 'pkgrel=27\n' in s;s=s.replace('pkgrel=27\n','pkgrel=28\n')
needle='\t0036-camss-dynamic-lens-shading.patch\n';assert s.count(needle)==1
s=s.replace(needle,needle+''.join('\t'+p.name+'\n' for p in [gammaPatch,newPatch]));at=s.rfind('"')
s=s[:at]+''.join(hashlib.sha512(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in [gammaPatch,newPatch])+s[at:];p.write_text(s)
p=HERE/'recipes/samurai-camera-config/APKBUILD';s=p.read_text();assert 'pkgrel=22\n' in s
p.write_text(s.replace('pkgrel=22\n','pkgrel=23\n').replace('99990.7.2-r27','99990.7.2-r28'))
for package,version in [('libcamera','99990.7.2-r28'),('samurai-camera-config','0.1.0-r23')]:
    recipe=HERE/'recipes'/package;p=recipe/'source-lock.json';state=json.loads(p.read_text())
    for source in recipe.iterdir():
        if source.is_file() and (source.name in state['source_files_sha256'] or source.suffix=='.patch'):
            state['source_files_sha256'][source.name]=hashlib.sha256(source.read_bytes()).hexdigest()
    state.update(stage=360,build_stage=360,package_version=version,candidate_only=True,installed=False,
        native_install_validation=None,actual_current_payload_validation=None,actual_signed_build_validation='reference/kernel360/package-build-validation.json')
    if package=='libcamera':state.update(maintained_source=str(tree),matched_camss_driver_stage=348,camss_ipa_pipeline_version=1,factory_mode_exposure_program_integrated=True,optional_static_ife_gamma_integrated=True)
    p.write_text(json.dumps(state,indent=2)+'\n')
for source in (HERE/'recipes/libcamera').iterdir():
    if source.is_file():shutil.copyfile(source,new/source.name)
config=new.parent/'samurai-camera-config360-r28';assert not config.exists();shutil.copytree(HERE/'recipes/samurai-camera-config',config)
report=dict(stage=360,framework_version='99990.7.2-r28',configuration_version='0.1.0-r23',baseline_framework='99990.7.2-r27',
    source=str(tree),delta_patches=[gammaPatch.name,newPatch.name],compared_source_files=len(names),differing_source_files=0,
    source_files=[dict(path=name,sha256=hashlib.sha256((tree/name).read_bytes()).hexdigest()) for name in names],
    default_profiles_unchanged=True,private_factory_tables_in_packages=False,matched_gamma_driver_stage=348,camss_ipa_pipeline_version=1,
    canonical_installed_recipes_unchanged=True,installed=False,passed=True)
(HERE/'package-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='source_files'},indent=2))
