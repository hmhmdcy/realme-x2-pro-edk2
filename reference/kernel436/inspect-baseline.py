from pathlib import Path
import hashlib,json,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;build=storage.mount.mounted_build();K=build.parent/'source354';T=build.parent/'libcamera435-gtm-history/src/libcamera-v0.7.2'
git=lambda p,*a:subprocess.check_output(['git','-C',str(p),*a],text=True).strip()
assert git(K,'rev-parse','HEAD')=='9bc07e6339128ae8d3525c7d5c9bca5d0fbc46f3' and not git(K,'status','--porcelain')
mirror_head=git(Path('/home/cy122/edk2-samurai/repo'),'rev-parse','HEAD')
assert mirror_head=='efd01b4cf0bbbbf966730c53cf381908408c7a27'
state=json.loads((HERE.parent/'kernel435/source-state.json').read_text())
for row in state['source_hashes']:assert hashlib.sha256((T/row['path']).read_bytes()).hexdigest()==row['sha256']
for rel in ['src/libcamera/pipeline/camss-vfe/camss_vfe.cpp','src/libcamera/pipeline/camss-vfe/meson.build','include/linux/qcom-ipe-a5.h']:
 p=T/rel
 for d in p.parents:assert not (d/'AGENTS.md').exists()
 out=P/'source-before'/rel;out.parent.mkdir(exist_ok=True,parents=True);out.write_bytes(p.read_bytes())
r=dict(stage=436,baseline435_sources_match=True,kernel_clean=True,mirror_head=mirror_head,mirror435_commit_present=False,previous_turn_classification='progress:obsolete intermediates cleaned;WSL writable and435 matched runtime hashes verified;quality defects remain',passed=True)
(HERE/'baseline-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
