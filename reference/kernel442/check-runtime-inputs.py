from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel441/check-runtime-inputs.py').read_text().replace('stage=441','stage=442')
source=source.replace("(HERE/'kernel-source-state.json')", "(HERE.parent/'kernel441/kernel-source-state.json')")
source=source.replace("(HERE.parent/'kernel434/capture-worker-body.py')", "(HERE.parent/'kernel434/capture-worker-body.py')")
exec(compile(source,str(HERE/'check-runtime-inputs.py'),'exec'))
