from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1]
path=repo/'linux-port/camera/libcamera/source-lock.json';d=json.loads(path.read_text());assert d['installed_framework_version']=='99990.7.2-r6'
d.update(deployment_stage=219,deployment_evidence='../../../reference/kernel219/r6-package-install-validation.json',
 source_files_sha256_scope='Historical stage213 three-patch source snapshot before native Quad changes; full current recipe inputs are locked separately',
 current_full_recipe_source_lock='../../packages/libcamera/source-lock.json')
path.write_text(json.dumps(d,indent=2)+'\n');print('Current r6 deployment metadata and historical source-hash scope made explicit')
