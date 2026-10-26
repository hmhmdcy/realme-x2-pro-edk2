from pathlib import Path
import ast,shutil
ref=Path(__file__).resolve().parent
archive=ref.parent.parent/'archive/NEXT-SESSION-through200-2026-10-15.md'
assert not archive.exists();shutil.copyfile(ref.parent.parent/'NEXT-SESSION.md',archive)
s=(ref.parent/'kernel191/probe-validity.py').read_text().replace('k191','k201').replace('stage=191','stage=201').replace('k189r2-reboot-runtime','k201-baseline')
ast.parse(s);(ref/'probe-validity.py').write_text(s)
s=(ref.parent/'kernel191/query-validity.py').read_text();ast.parse(s);(ref/'query-validity.py').write_text(s)
print('K201_FRESH_VALIDITY_QUERY_AND_EXACT200_CHECKPOINT_ARCHIVE_PREPARED')
