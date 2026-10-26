from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel431/build-candidate.py').read_text().replace('stage=431','stage=444')
exec(compile(source,str(HERE/'build-candidate.py'),'exec'))
state=json.loads((HERE/'source-state.json').read_text());state['build_pending']=False
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
