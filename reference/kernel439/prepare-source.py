"""Build front colour support on the verified current437 source cohort."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;volume=storage.mount.mounted_build().parent
old=volume/'libcamera437-awb-history';new=volume/'libcamera439-front-colour'
assert json.loads((HERE/'colour-math-validation.json').read_text())['passed']
baseline=json.loads((HERE.parent/'kernel437/source-state.json').read_text())
for row in baseline['source_hashes']:
 assert hashlib.sha256((old/'src/libcamera-v0.7.2'/row['path']).read_bytes()).hexdigest()==row['sha256']
assert not new.exists()
temporary=volume/'libcamera439-front-colour.preparing';assert not temporary.exists()
shutil.copytree(old,temporary,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
temporary.rename(new);tree=new/'src/libcamera-v0.7.2'
changed=[]
for name in ['colour_correction.h','colour_correction.cpp']:
 rel='src/ipa/libipa/'+name;shutil.copyfile(HERE/'libipa'/name,tree/rel);changed.append(rel)
for name in ['colour_correction_profile.h','colour_correction_profile.cpp','ipe_frame_history.h','ipe_tone_profile.h','ipe_tone_profile.cpp','camss.cpp']:
 rel='src/ipa/camss-vfe/'+name;shutil.copyfile(HERE/'camss'/name,tree/rel);changed.append(rel)
rel='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';shutil.copyfile(HERE/'pipeline/camss_vfe.cpp',tree/rel);changed.append(rel)
paths=sorted(set(changed)|{r['path'] for r in baseline['source_hashes']})
state={'stage':439,'source':str(tree),'baseline_stage':437,'source_prepared':True,'private_ipa_version':5,'changed_paths':changed,'source_hashes':[{'path':p,'sha256':hashlib.sha256((tree/p).read_bytes()).hexdigest()} for p in paths]}
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps({'source':str(tree),'changed_paths':changed}),flush=True)
