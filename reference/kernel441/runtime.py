"""Dispatch the one-shot 441 worker; never resume a completed transaction."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel430/runtime.py').read_text()
source=source.replace('k430-dc-topology-','k441-variable-pd10-')
source=source.replace("or p.suffix=='.bin'", "or p.suffix in ['.bin','.nv12','.pd10']")
source=source.replace("mode='w|gz'", "mode='w|gz',compresslevel=1")
source=source.replace('timeout=35',"timeout=180 if action=='collect' else 35")
exec(compile(source,str(HERE/'runtime.py'),'exec'))
