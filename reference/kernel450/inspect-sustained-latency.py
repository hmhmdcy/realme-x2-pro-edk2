"""Analyze only the new r3 cached log; no phone access or workload changes."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel449/inspect-sustained-latency.py').read_text().replace("'runtime-collected-r2'","'runtime-collected-r3'").replace('stage=449','stage=450')
exec(compile(source,str(HERE/'inspect-sustained-latency.py'),'exec'))
