from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel430/build-intree.py').read_text().replace("HERE/'source-state.json'","HERE/'kernel-source-state.json'").replace('stage=430','stage=431')
exec(compile(source,str(HERE/'build-intree.py'),'exec'))
