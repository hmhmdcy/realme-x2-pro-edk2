from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel447/check-runtime-inputs.py').read_text().replace('stage=447','stage=448')
exec(compile(source,str(HERE/'check-runtime-inputs.py'),'exec'))
