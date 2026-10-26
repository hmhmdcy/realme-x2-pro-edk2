from pathlib import Path
import importlib.util,json,sys
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel246');P.mkdir(mode=0o700,exist_ok=True)
name=sys.argv[1];assert Path(name).name==name and name.endswith('.py')
spec=importlib.util.spec_from_file_location('host',R/'host.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
x=host.ssh('python3 -',input=(R/name).read_bytes(),timeout=55);(P/(Path(name).stem+'-host-private.log')).write_bytes(x.stdout+x.stderr);v=json.loads(x.stdout)
if 'report' in v:(P/(Path(name).stem+'-private.json')).write_text(json.dumps(v,indent=2)+'\n');v=v['report']
(R/(Path(name).stem+'-validation.json')).write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
