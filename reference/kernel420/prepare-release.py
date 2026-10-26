"""Package the tested request channel, preserving all existing camera features."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];new=storage.candidate();old=new.parent/'libcamera418-request-iq'
assert json.loads((HERE/'initial-state-validation.json').read_text())['passed']
assert json.loads((HERE.parent/'kernel419/fault-validation.json').read_text())['passed']
assert json.loads((HERE.parent/'kernel418/source-validation.json').read_text())['passed']
assert not new.exists()
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';baseline=new.parent/'libcamera391-ipe-r30-built/src/libcamera-v0.7.2'
source=json.loads((HERE.parent/'kernel418/source-state.json').read_text())
for item in source['source_hashes']:assert hashlib.sha256((tree/item['path']).read_bytes()).hexdigest()==item['sha256']
for n in ['src/ipa/camss-vfe/camss.cpp','src/libcamera/pipeline_handler.cpp','src/libcamera/base/event_dispatcher_poll.cpp']:
 assert (tree/n).read_bytes()==(baseline/n).read_bytes()
for package in ['libcamera','samurai-camera-config']:
 dest=HERE/'recipes'/package;assert not dest.exists();shutil.copytree(HERE.parent/'kernel391/recipes'/package,dest)
recipe=HERE/'recipes/libcamera';patchfile=HERE.parent/'kernel418/0041-camss-ipe-request.patch';shutil.copyfile(patchfile,recipe/patchfile.name)
p=recipe/'APKBUILD';s=p.read_text();assert 'pkgrel=30\n' in s;s=s.replace('pkgrel=30\n','pkgrel=31\n')
needle='\t0040-camss-ipe-pipeline.patch\n';assert s.count(needle)==1;s=s.replace(needle,needle+'\t'+patchfile.name+'\n')
at=s.rfind('"');s=s[:at]+hashlib.sha512(patchfile.read_bytes()).hexdigest()+'  '+patchfile.name+'\n'+s[at:];p.write_text(s)
p=HERE/'recipes/samurai-camera-config/APKBUILD';s=p.read_text();assert 'pkgrel=25\n' in s;p.write_text(s.replace('pkgrel=25\n','pkgrel=26\n').replace('99990.7.2-r30','99990.7.2-r31'))
for package,version in [('libcamera','99990.7.2-r31'),('samurai-camera-config','0.1.0-r26')]:
 recipe=HERE/'recipes'/package;p=recipe/'source-lock.json';state=json.loads(p.read_text())
 for file in recipe.iterdir():
  if file.is_file() and (file.name in state['source_files_sha256'] or file.suffix=='.patch'):state['source_files_sha256'][file.name]=hashlib.sha256(file.read_bytes()).hexdigest()
 state.update(stage=420,build_stage=420,package_version=version,candidate_only=True,installed=False,native_install_validation=None,actual_current_payload_validation=None,actual_signed_build_validation='reference/kernel420/package-build-validation.json')
 if package=='libcamera':state.update(maintained_source=str(tree),matched_camss_driver_stage=389,matched_ipe_core_stage=419,matched_ipe_adapter_stage=419,ipe_media_request_included=True,automatic_ipa_iq_generation=False)
 p.write_text(json.dumps(state,indent=2)+'\n')
 p=recipe/'README.md';p.write_text('420候选：libcamera r31/config-stack r26收录418已验证的逐帧IPE请求通道，配套419生产驱动；完整IPA自动画质仍未接入。构建及部署状态以[420记录](../../../../reference/kernel420/README.md)为准。以下为历史。\n\n'+p.read_text())
for file in (HERE/'recipes/libcamera').iterdir():
 if file.is_file():shutil.copyfile(file,new/file.name)
config=new.parent/'samurai-camera-config420-r31';assert not config.exists();shutil.copytree(HERE/'recipes/samurai-camera-config',config)
for p in (HERE/'recipes/samurai-camera-config').iterdir():
 if p.name not in ['APKBUILD','source-lock.json','README.md']:assert p.read_bytes()==(HERE.parent/'kernel391/recipes/samurai-camera-config'/p.name).read_bytes()
r=dict(stage=420,framework_version='99990.7.2-r31',configuration_version='0.1.0-r26',baseline_framework='99990.7.2-r30',source=str(tree),
 tested418_source_hashes_match=True,request_patch_zero_fuzz_evidence_reused_from418=True,dispatcher_and_ipa_sources_unchanged=True,
 config_payload_unchanged_only_dependency_pin_updated=True,private_factory_tables_in_packages=False,automatic_ipa_iq_generation=False,installed=False,passed=True)
(HERE/'package-source-validation.json').write_text(json.dumps(r,indent=2)+'\n')
ipa=json.loads((HERE.parent/'kernel391/ipa-contract-validation.json').read_text());ipa.update(reused_unchanged_from_stage=391,reason='Only IPE request wrapper changes;no IPA numerical/interface change.Packaged signature checked separately.')
(HERE/'ipa-contract-validation.json').write_text(json.dumps(ipa,indent=2)+'\n')
s=(HERE.parent/'kernel391/build-packages.py').read_text().replace('r29/r24','r31/r26').replace('stage=391','stage=420').replace('391-r30','420-r31').replace('99990.7.2-r30','99990.7.2-r31').replace('0.1.0-r25','0.1.0-r26')
(HERE/'build-packages.py').write_text(s)
s=(HERE.parent/'kernel391/collect-packages.py').read_text().replace('stage=391','stage=420').replace('391-r30','420-r31').replace('camera391-package-prefix','camera420-package-prefix').replace('99990.7.2-r30','99990.7.2-r31').replace('0.1.0-r25','0.1.0-r26')
s=s.replace("kernel362/package-artifact-validation.json","kernel391/package-artifact-validation.json").replace("kernel362/runtime-repository/forward","kernel391/runtime-repository/forward").replace('camera362-package-prefix','camera391-package-prefix')
s=s.replace('CAMSS391','CAMSS420').replace('r29_r24','r30_r25').replace('identical_to_r29','identical_to_r30').replace('match_r29','match_r30')
(HERE/'collect-packages.py').write_text(s)
print(json.dumps(r,indent=2))
