from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel448/current-state.py').read_text().replace('stage=448','stage=450')
exec(compile(source,str(HERE/'current-state.py'),'exec'))
