from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel443/inspect-latency.py').read_text().replace('stage=443','stage=444')
exec(compile(source,str(HERE/'inspect-latency.py'),'exec'))
