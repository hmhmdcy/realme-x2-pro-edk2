from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel435/preflight.py').read_text().replace('stage=435','stage=439').replace('efd01b4cf0bbbbf966730c53cf381908408c7a27','41def451b6bc9716d94674cb77f6ead7a39490c1')
exec(compile(source,str(HERE/'preflight.py'),'exec'))
