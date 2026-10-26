from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel444/build-candidate.py').read_text().replace('stage=444','stage=445')
exec(compile(source,str(HERE/'build-candidate.py'),'exec'))
