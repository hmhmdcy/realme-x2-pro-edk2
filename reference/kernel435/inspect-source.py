from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;build=storage.mount.mounted_build();K=build.parent/'source354';old=build.parent/'libcamera431-pd10-auto/src/libcamera-v0.7.2'
git=lambda where,*a:subprocess.check_output(['git','-C',str(where),*a],text=True).strip()
assert git(K,'rev-parse','HEAD')=='9bc07e6339128ae8d3525c7d5c9bca5d0fbc46f3' and not git(K,'status','--porcelain')
assert git(Path('/home/cy122/edk2-samurai/repo'),'rev-parse','HEAD')=='efd01b4cf0bbbbf966730c53cf381908408c7a27'
state=json.loads((HERE.parent/'kernel431/source-state.json').read_text())
for row in state['source_hashes']:assert hashlib.sha256((old/row['path']).read_bytes()).hexdigest()==row['sha256']
out=P/'source-before';out.mkdir(exist_ok=True)
names=['include/libcamera/ipa/camss.mojom','src/libcamera/pipeline/camss-vfe/camss_vfe.cpp','src/ipa/camss-vfe/camss.cpp','src/ipa/camss-vfe/params.h','src/ipa/camss-vfe/parameter_encoder.cpp','src/ipa/camss-vfe/parameter_encoder.h']
names += [str(p.relative_to(old)) for p in (old/'src/ipa/libipa').glob('*tone*')]
names += [str(p.relative_to(old)) for p in (old/'src/ipa/libipa').glob('*tmc*')]
names += ['src/ipa/camss-vfe/'+n for n in ['ipe_tone_profile.cpp','ipe_tone_profile.h','statistics.h','ipe_frame_history.h','ipe_frame_history.cpp','ipe_numeric_history.h','meson.build'] if (old/'src/ipa/camss-vfe'/n).exists()]
for rel in names:
 p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((old/rel).read_bytes())
print(json.dumps(dict(stage=435,baseline_source=431,source_hashes_match=True,kernel_commit=git(K,'rev-parse','HEAD'),files=names,previous_turn_classification='progress:434 physical stock GTM, both banks and ACK/SOF verified, reopen driver fixed; production IPA binding pending',passed=True)))
