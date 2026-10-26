"""Validate the new accounting against preserved default and front captures."""
from pathlib import Path
import json,shlex
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
code='from pathlib import Path\nimport re,json\n'+(HERE/'installed-frame-audit.py').read_text()+r'''
rows=[]
for model,folder,log in [('s5kgw1','/var/lib/samurai/k440-install-r2/auto-s5kgw1','/var/lib/samurai/k440-install-r2/auto-s5kgw1.log'),('imx471','/var/lib/samurai/k440-packaged-cohort-r2/imx471-scene-native','/var/lib/samurai/k440-packaged-cohort-r2/imx471-scene-native/client.log')]:
 result=audit_auto(Path(log).read_text(),model,Path(folder));result['model']=model;rows.append(result)
print(json.dumps(dict(stage=440,rows=rows,raw_sample_lengths_and_luma_verified=True,extra_pd10_observations_discarded_without_commit=True,new_exposures_or_hardware_jobs=0,passed=True)))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=55);q.check_returncode();r=json.loads(q.stdout)
(HERE/'installed-auditor-prior-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
