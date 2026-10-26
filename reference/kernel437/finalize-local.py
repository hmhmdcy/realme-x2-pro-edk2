from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel436/finalize-local.py').read_text()
source=source.replace("'efd01b4cf0bbbbf966730c53cf381908408c7a27'","'bae4f75c941658dcc4cb21a152970b2c5f5f49b5'")
source=source.replace("['kernel435','kernel436']","['kernel437']")
source=source.replace("'archive/NEXT-SESSION-through435-2026-10-22.md'","'archive/NEXT-SESSION-through436-2026-10-22.md'")
source=source.replace('camera: restore stock main BLS before automatic tone and audit same-frame inputs','camera: retain AWB convergence for identical applied gains across GTM waits')
source=source.replace('stage=436','stage=437').replace('recovered435_public_files=True','baseline436_public_files_already_saved=True')
exec(compile(source,str(HERE/'finalize-local.py'),'exec'))
