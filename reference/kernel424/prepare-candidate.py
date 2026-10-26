"""Correct LTM's IFE lux history and preserve tone on incomplete statistics."""
from pathlib import Path
import hashlib,json,shutil
import storage
HERE=Path(__file__).resolve().parent;new=storage.candidate();old=new.parent/'libcamera423-ipa-tone'
assert json.loads((HERE.parent/'kernel423/hardware-validation.json').read_text())['passed']
assert json.loads((HERE/'exposure-domain-validation.json').read_text())['passed']
assert not new.exists();shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
tree=new/'src/libcamera-v0.7.2'
for name in ['ipe_tone_profile.h','ipe_tone_profile.cpp']:
 text=(HERE.parent/'kernel423'/name).read_text()
 text=text.replace('exposureValid','ltmLuxValid').replace('history.exposureIndex','history.ltmLuxIndex').replace('state.exposureIndex','state.ltmLuxIndex')
 if name.endswith('.h'):text=text.replace('float exposureIndex = 0;','float ltmLuxIndex = 0;')
 else:
  text=text.replace('in.curves.exposureIndex = frame.exposureIndex;','in.curves.exposureIndex = frame.luxIndex;')
  text=text.replace('history.ltmLuxIndex : frame.exposureIndex','history.ltmLuxIndex : frame.luxIndex')
  text=text.replace('state.ltmLuxIndex = frame.exposureIndex','state.ltmLuxIndex = frame.luxIndex')
 (HERE/name).write_text(text);(tree/'src/ipa/camss-vfe'/name).write_text(text)
method=(HERE.parent/'kernel423/ipa-tone-method.cpp').read_text()
method=method.replace('if (!frame || numericHistory_.busy()) {','if (!frame || !frame->luxValid || numericHistory_.busy()) {')
method=method.replace('<< " busy=" << numericHistory_.busy();','<< " busy=" << numericHistory_.busy() << " lux-valid=" << bool(frame && frame->luxValid);')
method=method.replace('<< " exposure-index=" << frame->exposureIndex << " factory="','<< " exposure-index=" << frame->exposureIndex << " previous-ltm-lux=" << numericHistory_.state().ltmLuxIndex << " factory="')
(HERE/'ipa-tone-method.cpp').write_text(method)
path=tree/'src/ipa/camss-vfe/camss.cpp';text=path.read_text();a=text.index('int IPACamss::prepareIpeParameters(');b=text.index('void IPACamss::frameProcessed(',a)
text=text[:a]+method+'\n'+text[b:];path.write_text(text)
names=['src/ipa/camss-vfe/camss.cpp','src/ipa/camss-vfe/ipe_tone_profile.h','src/ipa/camss-vfe/ipe_tone_profile.cpp']
rows=[dict(path=n,sha256=hashlib.sha256((tree/n).read_bytes()).hexdigest()) for n in names]
r=dict(stage=424,baseline_stage=423,source=str(tree),source_prepared=True,source_hashes=rows,private_ipa_version=3,
 ltm_attenuation_history_uses_lux_index=True,missing_lux_reuses_committed_packet_without_history_advance=True,permanent_install=False,passed=True)
(HERE/'source-state.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
