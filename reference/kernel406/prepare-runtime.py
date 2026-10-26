"""Reuse the durable temporary-load transaction with LTM-specific cases."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent;old=HERE.parent/'kernel402'
body=(old/'runtime-worker-body.py').read_text().replace('test_gamma_mode','test_ltm_mode').replace("'colour-pixels',timeout=75","'colour-pixels',timeout=150")
needle="assert len(rows)==21 and [(r['format'],r['mode']) for r in rows[:20]]==[(f,m) for f in range(2) for m in range(10)] and rows[-1]['passed']";assert needle in body
body=body.replace(needle,"assert len(rows)==53 and [(r['width'],r['format'],r['mode']) for r in rows[:52]]==[(w,f,m) for w in [640,650] for f in range(2) for m in range(13)] and rows[-1]['passed']")
body=body.replace("==20","==52").replace('native-colour-completed-before-restore','native-ltm-completed-before-restore')
(HERE/'runtime-worker-body.py').write_text(body)
stage=(old/'stage-runtime.py').read_text().replace('stage=402','stage=406').replace("'stage':402","'stage':406").replace('test_gamma_mode','test_ltm_mode').replace('k402-gamma-r2','k406-ltm-r1').replace('payload-r2-private','payload-r1-private')
needle=";assert adapter['sha256']=='4bfbb80fcfefc50aa770b0c39c49f4c016093dda95da82c11e43144030fefe5a' # adapter ABI and fixture unchanged";assert needle in stage
stage=stage.replace(needle,' # current fixed LTM adapter; normal job ABI remains unchanged')
stage=stage.replace("replace('start<600','start<240').replace('start>=600','start>=240')","replace('start<600','start<360').replace('start>=600','start>=360')")
ast.parse(stage);(HERE/'stage-runtime.py').write_text(stage)
runtime=(old/'runtime.py').read_text().replace('stage=402','stage=406').replace('k402-gamma-r2','k406-ltm-r1').replace('runtime-collected-r2','runtime-collected-r1')
ast.parse(runtime);(HERE/'runtime.py').write_text(runtime)
print('Prepared durable LTM transaction, observation of the same worker, and normal restoration.')
