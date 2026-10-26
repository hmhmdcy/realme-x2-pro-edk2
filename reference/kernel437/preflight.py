from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel435/preflight.py').read_text().replace('stage=435','stage=437').replace('efd01b4cf0bbbbf966730c53cf381908408c7a27','bae4f75c941658dcc4cb21a152970b2c5f5f49b5')
exec(compile(source,str(HERE/'preflight.py'),'exec'))
