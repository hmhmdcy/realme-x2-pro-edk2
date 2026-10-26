"""Use the audited FAT/CPIO packager with explicit current rollback identities."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
script=(HERE.parent/'kernel298/package-boot-candidate.py').read_text().replace('298','363')
# Preserve the already deployed k298 rollback rather than an older camera tree.
script=script.replace("PRIVATE.parent/'kernel290/logdump-k290-candidate-private.img'", "PRIVATE.parent/'kernel298/logdump-k298-candidate-private.img'")
import json
old=json.loads((HERE.parent/'kernel298/boot-package-validation.json').read_text())
script=script.replace('0f169a331d1c4aac98cd67f636c9f30dd0c727ffc20a6031e4de142d7f57396a',old['logdump_sha256'])
exec(compile(script,str(HERE/'package-boot-candidate.py'),'exec'))
