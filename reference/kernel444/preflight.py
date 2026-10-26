from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel441/preflight.py').read_text().replace('stage=441','stage=444')
exec(compile(source,str(HERE/'preflight.py'),'exec'))
