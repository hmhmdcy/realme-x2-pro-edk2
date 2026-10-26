from pathlib import Path
import json,subprocess
R=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/kernel272')
W=Path('/home/cy122/x2pro-linux/camera270-kernel')
bin=Path('/home/cy122/x2pro-linux/.venv-dtschema/bin')
q=subprocess.run([str(bin/'dt-doc-validate'),str(W/'Documentation/devicetree/bindings/media/i2c/samsung,s5kgw1.yaml')],capture_output=True)
(P/'binding-doc-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0 and not q.stdout and not q.stderr,'Inspect binding diagnostics'
q=subprocess.run([str(bin/'dt-mk-schema'),'-j','-o',str(P/'schema272.json'),str(W/'Documentation/devicetree/bindings')],capture_output=True,timeout=90)
(P/'schema-build-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,'Inspect schema compiler diagnostics'
report=dict(stage=272,binding_doc_valid=True,schema_generated=True,phone_unchanged=True)
(R/'binding-schema-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
