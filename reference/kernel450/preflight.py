from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel448/preflight.py').read_text().replace('stage=448','stage=450').replace('k448-adopted','k449-adopted')
exec(compile(source,str(HERE/'preflight.py'),'exec'))
