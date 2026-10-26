from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel435/preflight.py').read_text().replace('stage=435','stage=438').replace('efd01b4cf0bbbbf966730c53cf381908408c7a27','5609244b81d2a417f374683abb79b42d4d47f1d7')
exec(compile(source,str(HERE/'preflight.py'),'exec'))
