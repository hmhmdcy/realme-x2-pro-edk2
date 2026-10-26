from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel435/preflight.py').read_text().replace('stage=435','stage=440').replace('efd01b4cf0bbbbf966730c53cf381908408c7a27','01a71e6fd9ac33b0f91539354f540b39213eafc3')
source=source.replace('progress:434 physical GTM/banks/SOF and driver reopen fix verified','progress:439 front automatic colour and tone verified;440 signed package cohort and offline contracts prepared')
exec(compile(source,str(HERE/'preflight.py'),'exec'))
