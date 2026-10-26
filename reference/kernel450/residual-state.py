from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel449/residual-state.py').read_text().replace('stage=449','stage=450').replace('k449-lifecycle-user-','k450-stats-retirement-').replace('k449-user-','k450-user-')
exec(compile(source,str(HERE/'residual-state.py'),'exec'))
