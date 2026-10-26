from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel444/check-reentry.py').read_text().replace('stage=444','stage=447')
exec(compile(source,str(HERE/'check-reentry.py'),'exec'))
