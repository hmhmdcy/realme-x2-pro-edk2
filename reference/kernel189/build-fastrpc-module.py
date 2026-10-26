"""Reuse the established same-kernel module build checks for the freezer candidate."""
from pathlib import Path

ref=Path(__file__).resolve().parent
data=(ref.parent/'kernel186/build-fastrpc-module.py').read_text()
data=data.replace('kernel186','kernel189').replace('fastrpc-k186-private.ko','fastrpc-k189-private.ko')
data=data.replace('stage=186','stage=189')
exec(compile(data,str(ref/'build-fastrpc-module.py'),'exec'))
