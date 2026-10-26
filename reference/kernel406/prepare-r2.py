"""Start a separate transaction only after R1's known terminal restoration."""
from pathlib import Path
import ast,json
HERE=Path(__file__).resolve().parent
r=json.loads((HERE/'runtime-validation-r1.json').read_text());assert r['state']['terminal'] and r['state']['normal395_restored'] and not any(r[k] for k in ['worker_live','client_live','collector_live'])
stage=(HERE/'stage-runtime.py').read_text().replace('k406-ltm-r1','k406-ltm-r2').replace('payload-r1-private','payload-r2-private').replace("HERE/'staging-validation.json'","HERE/'staging-validation-r2.json'")
ast.parse(stage);(HERE/'stage-runtime-r2.py').write_text(stage)
runtime=(HERE/'runtime.py').read_text().replace('k406-ltm-r1','k406-ltm-r2').replace('runtime-collected-r1','runtime-collected-r2').replace("HERE/'staging-validation.json'","HERE/'staging-validation-r2.json'").replace("HERE/'runtime-validation.json'","HERE/'runtime-validation-r2.json'")
ast.parse(runtime);(HERE/'runtime-r2.py').write_text(runtime)
print('Prepared separate R2 with unchanged client/adapter and explicit-IP core correction.')
