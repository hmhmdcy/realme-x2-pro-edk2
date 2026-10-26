from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel430/runtime.py').read_text().replace('k430-dc-topology-','k436-tone-domain-').replace("or p.suffix=='.bin'","or p.suffix in ['.bin','.nv12','.pd10']")
source=source.replace('timeout=35','timeout=60 if action==\'collect\' else 35')
exec(compile(source,str(HERE/'runtime.py'),'exec'))
