from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel442/runtime.py').read_text().replace('k442-callback-timing-','k449-lifecycle-user-')
exec(compile(source,str(HERE/'runtime.py'),'exec'))
