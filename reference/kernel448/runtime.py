from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel442/runtime.py').read_text().replace('k442-callback-timing-','k448-capacity-lease-')
exec(compile(source,str(HERE/'runtime.py'),'exec'))
