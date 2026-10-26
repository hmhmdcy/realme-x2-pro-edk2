from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel444/build-candidate.py').read_text().replace('stage=444','stage=450')
exec(compile(source,str(HERE/'build-candidate.py'),'exec'))
