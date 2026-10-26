from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel442/runtime.py').read_text().replace('k442-callback-timing-','k450-stats-retirement-')
exec(compile(source,str(HERE/'runtime.py'),'exec'))
