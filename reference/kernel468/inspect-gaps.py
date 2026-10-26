"""Apply the retained gap parser to the new mode2 originals."""
from pathlib import Path
import hashlib
HERE=Path(__file__).resolve().parent
path=HERE.parent/'kernel467/inspect-gaps.py';raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='f44aaf0b29139ece8d63b46877dbc7307d79c4e7c636880791fbe76c9f668e4f'
source=raw.decode().replace('kernel467','kernel468').replace('runtime-collected-r1','runtime-collected-r2')
source=source.replace('len(dq)==65','len(dq)==66').replace('stage=467','stage=468')
source=source.replace('full_dq=65','full_dq=66').replace('source_completed_full_not_ipe_or_consumed=1','source_completed_full_not_ipe_or_consumed=2')
exec(compile(source,'retained467-full-gaps-mode2','exec'))
