from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel446/inspect-latency.py').read_text().replace('stage=446','stage=447')
exec(compile(source,str(HERE/'inspect-latency.py'),'exec'))
