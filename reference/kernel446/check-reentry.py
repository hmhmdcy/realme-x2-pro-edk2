from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel445/check-reentry.py').read_text().replace('stage=445','stage=446')
exec(compile(source,str(HERE/'check-reentry.py'),'exec'))
