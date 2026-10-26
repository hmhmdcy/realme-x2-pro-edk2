"""Reuse the scoped public export without staging, committing or pushing."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel441/finish-local.py').read_text().replace('stage=441','stage=442')
exec(compile(source,str(HERE/'finish-local.py'),'exec'))
