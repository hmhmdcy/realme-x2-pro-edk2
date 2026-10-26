from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel431/build-candidate.py').read_text().replace('stage=431','stage=441')
exec(compile(source,str(HERE/'build-candidate.py'),'exec'))
