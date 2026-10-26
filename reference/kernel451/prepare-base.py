from pathlib import Path
import hashlib,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;volume=storage.mount.mounted_build().parent
old=volume/'libcamera450-stats-retirement';new=storage.candidate()
assert not new.exists(),'Do not overwrite a candidate'
state=json.loads((HERE.parent/'kernel450/source-state.json').read_text())
for row in state['source_hashes']:assert hashlib.sha256((old/'src/libcamera-v0.7.2'/row['path']).read_bytes()).hexdigest()==row['sha256']
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[s for s in n if s=='pkg' or s.startswith('pkg-before') or s=='__pycache__'])
state.update(stage=451,source=str(new/'src/libcamera-v0.7.2'),baseline_stage=450,source_baseline_stage=450,build_pending=True,changed_this_stage=[],proxy_optimization_pending=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(dict(stage=451,baseline450_preserved=True,phone_accessed=False,passed=True)))
