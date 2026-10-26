from pathlib import Path
import hashlib,json,re,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;new=storage.candidate();old=new.parent/'libcamera387-ipe-built';base=new.parent/'libcamera362-serialized-built/src/libcamera-v0.7.2'
assert json.loads((HERE/'initial-state-validation.json').read_text())['passed'] and not new.exists()
assert json.loads((HERE.parent/'kernel390/hardware-validation.json').read_text())['passed']
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';patchfile=HERE/'0040-camss-ipe-pipeline.patch';shutil.copyfile(HERE.parent/'kernel387/camss-ipe-pipeline.patch',patchfile)
names=re.findall(r'^\+\+\+ b/(.+)$',patchfile.read_text(),re.M);assert len(names)==4
check=new.parent/'patch-check391';assert not check.exists();check.mkdir()
for name in names:
 target=check/name;target.parent.mkdir(parents=True,exist_ok=True)
 if (base/name).exists():shutil.copyfile(base/name,target)
q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(patchfile)],cwd=check,capture_output=True);(P/'patch-apply.log').write_bytes(q.stdout+q.stderr);assert not q.returncode
assert all((check/n).read_bytes()==(tree/n).read_bytes() for n in names)
for name in ['src/ipa/camss-vfe/camss.cpp','src/libcamera/base/event_dispatcher_poll.cpp','src/libcamera/pipeline_handler.cpp']:assert (base/name).read_bytes()==(tree/name).read_bytes()
for package in ['libcamera','samurai-camera-config']:
 dest=HERE/'recipes'/package;assert not dest.exists();shutil.copytree(HERE.parent/'kernel362/recipes'/package,dest)
recipe=HERE/'recipes/libcamera';shutil.copyfile(patchfile,recipe/patchfile.name)
p=recipe/'APKBUILD';s=p.read_text();assert 'pkgrel=29\n' in s;s=s.replace('pkgrel=29\n','pkgrel=30\n')
needle='\t0039-synchronous-ipa-reentrancy.patch\n';assert s.count(needle)==1;s=s.replace(needle,needle+'\t'+patchfile.name+'\n');at=s.rfind('"');s=s[:at]+hashlib.sha512(patchfile.read_bytes()).hexdigest()+'  '+patchfile.name+'\n'+s[at:];p.write_text(s)
p=HERE/'recipes/samurai-camera-config/APKBUILD';s=p.read_text();assert 'pkgrel=24\n' in s;p.write_text(s.replace('pkgrel=24\n','pkgrel=25\n').replace('99990.7.2-r29','99990.7.2-r30'))
for package,version in [('libcamera','99990.7.2-r30'),('samurai-camera-config','0.1.0-r25')]:
 recipe=HERE/'recipes'/package;p=recipe/'source-lock.json';state=json.loads(p.read_text())
 for file in recipe.iterdir():
  if file.is_file() and (file.name in state['source_files_sha256'] or file.suffix=='.patch'):state['source_files_sha256'][file.name]=hashlib.sha256(file.read_bytes()).hexdigest()
 state.update(stage=391,build_stage=391,package_version=version,candidate_only=True,installed=False,native_install_validation=None,actual_current_payload_validation=None,actual_signed_build_validation='reference/kernel391/package-build-validation.json')
 if package=='libcamera':state.update(maintained_source=str(tree),matched_camss_driver_stage=389,matched_platform_deployment_stage=390,ipe_pipeline_included=True,isolated_request_queue_verified=True,common_request_order_preserved=True)
 p.write_text(json.dumps(state,indent=2)+'\n')
for file in (HERE/'recipes/libcamera').iterdir():
 if file.is_file():shutil.copyfile(file,new/file.name)
config=new.parent/'samurai-camera-config391-r30';assert not config.exists();shutil.copytree(HERE/'recipes/samurai-camera-config',config)
defaults=[p for p in (HERE/'recipes/samurai-camera-config').iterdir() if p.name not in ['APKBUILD','source-lock.json']]
assert all(p.read_bytes()==(HERE.parent/'kernel362/recipes/samurai-camera-config'/p.name).read_bytes() for p in defaults)
report=dict(stage=391,framework_version='99990.7.2-r30',configuration_version='0.1.0-r25',baseline_framework='99990.7.2-r29',source=str(tree),changed_files=names,zero_fuzz_patch_reproduces_validated387_source=True,dispatcher_and_ipa_sources_unchanged=True,config_payload_unchanged_only_exact_dependency_pin_updated=True,private_factory_tables_in_packages=False,installed=False,passed=True)
(HERE/'package-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
ipa=json.loads((HERE.parent/'kernel362/ipa-contract-validation.json').read_text());ipa.update(reused_unchanged_from_stage=362,reason='IPE queue integration changes no IPA algorithm/interface; packaged signature will be checked against packaged core')
(HERE/'ipa-contract-validation.json').write_text(json.dumps(ipa,indent=2)+'\n')
script=(HERE.parent/'kernel362/build-packages.py').read_text().replace('stage=362','stage=391').replace('packages362-r29','packages391-r30').replace('packages-config362-r29','packages-config391-r30').replace('samurai-camera-config362-r29','samurai-camera-config391-r30').replace("'99990.7.2-r29'","'99990.7.2-r30'").replace("'0.1.0-r24'","'0.1.0-r25'")
(HERE/'build-packages.py').write_text(script);print(json.dumps(report,indent=2))
