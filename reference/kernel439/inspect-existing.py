from pathlib import Path
import hashlib,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;T=storage.candidate()/'src/libcamera-v0.7.2'
assert subprocess.check_output(['git','-C','/home/cy122/edk2-samurai/repo','rev-parse','HEAD'],text=True).strip()=='41def451b6bc9716d94674cb77f6ead7a39490c1'
for row in json.loads((HERE.parent/'kernel437/source-state.json').read_text())['source_hashes']:assert hashlib.sha256((T/row['path']).read_bytes()).hexdigest()==row['sha256']
rels=['src/ipa/camss-vfe/camss.cpp','src/ipa/camss-vfe/colour_correction_profile.cpp','src/ipa/camss-vfe/colour_correction_profile.h','src/ipa/camss-vfe/ipe_tone_profile.cpp','src/ipa/camss-vfe/ipe_tone_profile.h','src/ipa/camss-vfe/ipe_frame_history.h','src/ipa/libipa/colour_correction.cpp','src/ipa/libipa/colour_correction.h','src/libcamera/pipeline/camss-vfe/camss_vfe.cpp']
for rel in rels:
 p=T/rel
 for parent in p.parents:assert not (parent/'AGENTS.md').exists()
 out=P/'source-before'/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(p.read_bytes())
(HERE/'baseline-validation.json').write_text(json.dumps(dict(stage=439,source437_matches=True,baseline438_data_only_reused=True,previous_turn_classification='progress:438 stock wide/tele tone plus real PD10 and final history verified96 scenes91 math;front native nonidentity IPE CCM pending',passed=True),indent=2)+'\n')
print('Current437 source cohort and438 checkpoint verified; front adapter interfaces saved')
