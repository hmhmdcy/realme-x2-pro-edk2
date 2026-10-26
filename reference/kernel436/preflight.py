from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel435/preflight.py').read_text().replace('stage=435','stage=436')
exec(compile(source,str(HERE/'preflight.py'),'exec'))
