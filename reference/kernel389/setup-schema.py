from pathlib import Path
import json,subprocess
import host
P=host.PRIVATE;python=P/'schema-venv/bin/python'
with (P/'schema-install.log').open('xb') as log:
 q=subprocess.run([str(python),'-m','pip','install','dtschema','--report',str(P/'schema-install-report.json')],stdout=log,stderr=subprocess.STDOUT)
assert not q.returncode
q=subprocess.run([str(python),'-c','import importlib.metadata,json;print(json.dumps({n:importlib.metadata.version(n) for n in ["dtschema","jsonschema","pylibfdt"]}))'],capture_output=True);q.check_returncode()
(P/'schema-versions.json').write_bytes(q.stdout);print(q.stdout.decode())
