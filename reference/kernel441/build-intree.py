"""Reuse the matched in-tree W=1/Werror build and output restoration."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel430/build-intree.py').read_text().replace('stage=430','stage=441').replace("HERE/'source-state.json'","HERE/'kernel-source-state.json'")
source=source.replace('camss_ds4_capture_candidate=True,','camss_ds4_capture_candidate=True,variable_pd10_geometry_candidate=True,')
exec(compile(source,str(HERE/'build-intree.py'),'exec'))
