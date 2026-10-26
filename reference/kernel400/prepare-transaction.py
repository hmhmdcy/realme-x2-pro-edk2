"""Adapt the existing private-load/restore transaction to sixteen chain frames."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
body=(HERE.parent/'kernel397/runtime-worker-body.py').read_text().replace('test_cc_mode','test_chain_mode')
body=body.replace("assert len(rows)==5 and [r['mode'] for r in rows[:4]]==[0,1,2,3] and rows[-1]['passed']","assert len(rows)==17 and [(r['format'],r['mode']) for r in rows[:16]]==[(f,m) for f in range(2) for m in range(8)] and rows[-1]['passed']")
body=body.replace("s['direct_completed']==4 and s['starts']==s['stops']==4","s['direct_completed']==16 and s['starts']==s['stops']==16")
assert "s['direct_completed']==16" in body
(HERE/'runtime-worker-body.py').write_text(body)
stage=(HERE.parent/'kernel397/stage-runtime.py').read_text().replace('stage=397','stage=400').replace("\"'stage':397\"","\"'stage':400\"").replace('k397-colour-r1','k400-chain-r1').replace('test_cc_mode','test_chain_mode')
# Reuse the already observed normal399 build and the completed400 test build.
# Generate the current runtime observer directly; it must not regenerate an
# older395 observer with incompatible assumptions.
start=stage.index("runtime=(HERE.parent/'kernel395/runtime.py')");end=stage.index('ast.parse(runtime);',start)
stage=stage[:start]+"runtime=(HERE.parent/'kernel397/runtime.py').read_text().replace('k397-colour-r1','k400-chain-r1').replace('stage=397','stage=400')\n"+stage[end:]
ast.parse(stage);(HERE/'stage-runtime.py').write_text(stage)
print('Prepared distinct k400 transaction; launch remains gated on completed build/staging.')
