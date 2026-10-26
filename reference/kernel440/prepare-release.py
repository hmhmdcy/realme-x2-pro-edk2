"""Reproduce439 from the formal patch chain, then prepare r32/r27 packages."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,tempfile
import host,storage
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE;volume=storage.mount.mounted_build().parent;tree=storage.candidate()/'src/libcamera-v0.7.2';baseline=volume/'libcamera420-request-r31/src/libcamera-v0.7.2'
assert json.loads((HERE/'initial-state-validation.json').read_text())['passed'] and json.loads((HERE.parent/'kernel439/hardware-validation.json').read_text())['passed']
patches=[]
for stage,number in [(421,42),(422,43),(423,44),(424,45),(431,46),(435,47),(436,48),(437,49),(439,50)]:
 paths=list((HERE.parent/('kernel'+str(stage))).glob(f'{number:04d}-*.patch'));assert len(paths)==1;patches+=paths
paths=set()
for patch in patches:
 for line in patch.read_text().splitlines():
  if line.startswith(('--- a/','+++ b/')):
   rel=line[6:].split('\t')[0];assert not rel.startswith('/') and '..' not in Path(rel).parts;paths.add(rel)
with tempfile.TemporaryDirectory(prefix='release440-patch-',dir=volume/'tmp') as temporary:
 dest=Path(temporary)
 for rel in paths:
  p=baseline/rel
  if p.is_file():(dest/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest/rel)
 logs=[]
 for patch in patches:
  q=subprocess.run(['patch','--batch','--fuzz=0','-p1'],cwd=dest,input=patch.read_bytes(),capture_output=True);log=(q.stdout+q.stderr).decode();logs.append(log)
  assert not q.returncode and 'fuzz' not in log.lower() and 'offset' not in log.lower(),(patch.name,log)
 for rel in paths:assert (dest/rel).read_bytes()==(tree/rel).read_bytes(),rel
 (P/'patch-chain.log').write_text('\n'.join(logs))
report={'stage':440,'passed':True,'baseline_formal_source_stage':420,'final_source_stage':439,'additional_patches':len(patches),'compared_source_files':len(paths),'zero_fuzz_offset_replay_byte_identical':True,'patches':[p.name for p in patches]}
(HERE/'patch-chain-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for package in ['libcamera','samurai-camera-config']:
 dest=HERE/'recipes'/package;assert not dest.exists();shutil.copytree(ROOT/'linux-port/packages'/package,dest)
recipe=HERE/'recipes/libcamera'
for p in patches:shutil.copyfile(p,recipe/p.name)
p=recipe/'APKBUILD';s=p.read_text();assert 'pkgrel=31\n' in s;s=s.replace('pkgrel=31\n','pkgrel=32\n');needle='\t0041-camss-ipe-request.patch\n';assert s.count(needle)==1;s=s.replace(needle,needle+''.join('\t'+p.name+'\n' for p in patches));at=s.rfind('"');s=s[:at]+''.join(hashlib.sha512(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in patches)+s[at:];p.write_text(s)
p=HERE/'recipes/samurai-camera-config/APKBUILD';s=p.read_text();assert 'pkgrel=26\n' in s;p.write_text(s.replace('pkgrel=26\n','pkgrel=27\n').replace('99990.7.2-r31','99990.7.2-r32'))
for package,version in [('libcamera','99990.7.2-r32'),('samurai-camera-config','0.1.0-r27')]:
 recipe=HERE/'recipes'/package;p=recipe/'source-lock.json';state=json.loads(p.read_text())
 for file in recipe.iterdir():
  if file.is_file() and (file.name in state['source_files_sha256'] or file.suffix=='.patch'):state['source_files_sha256'][file.name]=hashlib.sha256(file.read_bytes()).hexdigest()
 state.update(stage=440,build_stage=440,package_version=version,candidate_only=True,installed=False,native_install_validation=None,actual_current_payload_validation=None,actual_signed_build_validation='reference/kernel440/package-build-validation.json')
 if package=='libcamera':state.update(maintained_source=str(tree),matched_camss_driver_stage=434,matched_ipe_core_stage=434,matched_ipe_adapter_stage=434,automatic_ipa_iq_generation=True,private_ipa_version=5,original_factory_data_private_overrides=True)
 p.write_text(json.dumps(state,indent=2)+'\n')
 p=recipe/'README.md';p.write_text('440候选：r32/r27包含已验证439自动PD10/tone/前摄IPE CCM，匹配434模块；原厂表保留本机私有override。当前构建、实拍和部署见[440记录](../../../../reference/kernel440/README.md)。以下为历史。\n\n'+p.read_text())
# Reuse the439 build rather than making another full source/object copy.
source=storage.candidate();assert not (source/'pkg').exists()
for file in (HERE/'recipes/libcamera').iterdir():
 if file.is_file():shutil.copyfile(file,source/file.name)
config=volume/'samurai-camera-config440-r32';assert not config.exists();shutil.copytree(HERE/'recipes/samurai-camera-config',config)
for model,stage in [('s5kgw1',437),('imx319',438),('s5k3m5',438),('imx471',439)]:
 original=P.parent/f'kernel{stage}'/f'factory-{model}-private.yaml';shutil.copyfile(original,P/f'factory-{model}-private.yaml')
r={'stage':440,'passed':True,'framework_version':'99990.7.2-r32','configuration_version':'0.1.0-r27','source':str(tree),'new_source_clone_created':False,'formal420_to439_patch_chain_byte_identical':True,'private_profiles_reused_from':{'s5kgw1':437,'imx319':438,'s5k3m5':438,'imx471':439},'public_generic_configs_unchanged':True,'private_factory_tables_in_packages':False,'matched_driver_stage':434,'installed':False}
(HERE/'package-source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
