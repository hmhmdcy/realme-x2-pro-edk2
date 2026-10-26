from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel436/finalize-local.py').read_text()
source=source.replace("'efd01b4cf0bbbbf966730c53cf381908408c7a27'","'5609244b81d2a417f374683abb79b42d4d47f1d7'")
source=source.replace("['kernel435','kernel436']","['kernel438']")
source=source.replace("'archive/NEXT-SESSION-through435-2026-10-22.md'","'archive/NEXT-SESSION-through437-2026-10-22.md'")
source=source.replace('camera: restore stock main BLS before automatic tone and audit same-frame inputs','camera: verify stock wide and tele tone with real PD10 and applied history')
source=source.replace('stage=436','stage=438').replace('recovered435_public_files=True','reused437_userspace_without_source_changes=True')
exec(compile(source,str(HERE/'finalize-local.py'),'exec'))
