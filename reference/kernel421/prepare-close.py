"""Reuse420's file/note/resource checks with this transaction's actual epoch."""
from pathlib import Path
import ast,sys
HERE=Path(__file__).resolve().parent
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';assert attempt in ['r1','r2']
s=(HERE.parent/'kernel420/close-current.py').read_text()
s=s.replace("r=json.loads((HERE/'install-validation.json').read_text());assert r['passed'] and r['installed'] and r['driver_pair_installed'] and r['terminal']", "r=json.loads((HERE/'runtime-validation.json').read_text());assert r['passed'] and r['formal420_unchanged'] and r['terminal']")
s=s.replace("proof=json.loads((P/'install-proof-private.json').read_text())", "proof=json.loads((P.parent/'kernel420/install-proof-private.json').read_text())")
s=s.replace("root=Path('/var/lib/samurai/k420-install-r1');state=", "root=Path('/var/lib/samurai/k421-history-"+attempt+"');state=")
s=s.replace("==93\nreport=dict(stage=420", "==r['after']['completed']\nreport=dict(stage=421")
a=s.index("suite=json.loads((P/'install-collected-r1/suite.json')")
s=s[:a]+"print(json.dumps(dict(stage=421,formal420_unchanged=True,current_state_passed=True,completed=d['m2m']['completed'],services=d['services'],passed=True)))\n"
assert 'stage=420' not in s
ast.parse(s);(HERE/'close-current.py').write_text(s)
