"""Authenticated read-only collector runner with private raw output."""
from pathlib import Path
import importlib.util,json,sys
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel243');P.mkdir(mode=0o700,exist_ok=True)
name=sys.argv[1];assert Path(name).name==name and name.endswith('.py')
spec=importlib.util.spec_from_file_location('host',R.parent/'kernel240/host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
try:p=host.ssh('python3 -',input=(R/name).read_bytes(),timeout=55)
except Exception:raise RuntimeError('Collector failed; inspect private transport receipt before retry') from None
(P/(Path(name).stem+'-host-private.log')).write_bytes(p.stdout+p.stderr)
v=json.loads(p.stdout)
if 'report' in v:
 (P/(Path(name).stem+'-private.json')).write_text(json.dumps(v,indent=2)+'\n');v=v['report']
(R/(Path(name).stem+'-validation.json')).write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
