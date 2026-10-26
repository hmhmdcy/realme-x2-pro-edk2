"""Require coarse PD10 for processed output, while retaining RAW-only capture."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;volume=storage.mount.mounted_build().parent;old=volume/'libcamera439-front-colour';new=volume/'libcamera440-release-r32';assert not new.exists()
failed=json.loads((HERE/'runtime-r1-validation.json').read_text());assert failed['state']['terminal'] and not failed['worker_live'] and not failed['client_live'] and not failed['state']['passed']
assert failed['state']['formal_modules_restored'] and failed['state']['services_restored'] and not failed['state']['new_faults'] and failed['state']['taint_after']==0
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';rel='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';path=tree/rel;before=path.read_text();text=before
def replace(a,b):
 global text
 assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b)
replace('bool rawEnabled_ = false, processedEnabled_ = true;', 'bool rawEnabled_ = false, processedEnabled_ = true;\n bool requiresPd10() const { return processedEnabled_ && sensorConfiguration_.pd10; }')
replace('if(d->sensorConfiguration_.pd10) {','if(d->requiresPd10()) {')
replace('if(!d->coarse_ || !d->ipe_ || !d->processedEnabled_ || d->output_!=Size(640,480))','if(!d->coarse_ || !d->ipe_ || d->output_!=Size(640,480))')
replace('if(d->sensorConfiguration_.pd10!=d->coarseEnabled_)','if(d->requiresPd10()!=d->coarseEnabled_)')
path.write_text(text);patch=''.join(difflib.unified_diff(before.splitlines(keepends=True),text.splitlines(keepends=True),fromfile='a/'+rel,tofile='b/'+rel));patchname='0051-camss-raw-only-pd10-policy.patch';(HERE/patchname).write_text(patch)
state=json.loads((HERE.parent/'kernel439/source-state.json').read_text());state.update(stage=440,source=str(tree),baseline_stage=439,changed_paths=[rel])
for row in state['source_hashes']:row['sha256']=hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
recipe=HERE/'recipes/libcamera';shutil.copyfile(HERE/patchname,recipe/patchname);p=recipe/'APKBUILD';s=p.read_text();needle='\t0050-camss-front-ipe-colour.patch\n';assert s.count(needle)==1;s=s.replace(needle,needle+'\t'+patchname+'\n');at=s.rfind('"');s=s[:at]+hashlib.sha512(patch.encode()).hexdigest()+'  '+patchname+'\n'+s[at:];p.write_text(s)
for p in recipe.iterdir():
 if p.is_file():shutil.copyfile(p,new/p.name)
lock=recipe/'source-lock.json';data=json.loads(lock.read_text());data.update(maintained_source=str(tree),raw_only_pd10_requirement_fixed=True);data['source_files_sha256'].update({n:hashlib.sha256((recipe/n).read_bytes()).hexdigest() for n in ['APKBUILD',patchname]});lock.write_text(json.dumps(data,indent=2)+'\n');shutil.copyfile(lock,new/'source-lock.json')
for name in ['package-build','package-artifact','package-source','packaged-contract','build','ipa','source']:
 file=HERE/(name+'-validation.json')
 if file.exists():shutil.copyfile(file,P/(name+'-r1-validation-private.json'))
source=json.loads((HERE/'package-source-validation.json').read_text());source.update(source=str(tree),new_source_clone_created=True,source_clone_reason='Preserve439 after integration exposed RAW-only PD10 policy defect',additional_raw_only_policy_patch=patchname,automatic_processing_path_unchanged=True,installed=False);(HERE/'package-source-validation.json').write_text(json.dumps(source,indent=2)+'\n')
r={'stage':440,'passed':True,'cause':'PD10 request from the IPA was incorrectly treated as mandatory for RAW-only despite no IPE consumer','changed_source_files':[rel],'processed_path_requirement_retained':True,'raw_metadata_and_observation_discard_paths_unchanged':True,'ipa_mojom_and_kernel_unchanged':True,'previous439_source_preserved':True,'installed':False}
(HERE/'raw-policy-source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
