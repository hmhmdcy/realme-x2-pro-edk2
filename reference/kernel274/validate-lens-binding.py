from pathlib import Path
import json,subprocess
import host
R=Path(__file__).resolve().parent;W=Path('/home/cy122/x2pro-linux/camera270-kernel');bin=Path('/home/cy122/x2pro-linux/.venv-dtschema/bin')
binding=W/'Documentation/devicetree/bindings/media/i2c/onnn,lc898219xi.yaml'
q=subprocess.run([str(bin/'dt-doc-validate'),str(binding)],capture_output=True)
(host.PRIVATE/'lens-binding-doc-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and not q.stdout and not q.stderr,'Inspect lens binding diagnostics'
report=dict(stage=274,binding_doc_valid=True,not_deployed=True)
(R/'lens-binding-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
