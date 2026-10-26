"""Verify formal restoration after the new cancellation and dispatch cases."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel441/current-state.py').read_text().replace('stage=441','stage=442')
exec(compile(source,str(HERE/'current-state.py'),'exec'))
