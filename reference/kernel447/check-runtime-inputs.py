from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel445/check-runtime-inputs.py').read_text().replace('stage=445','stage=447')
source=source.replace("HERE/'focus-validation.json'", "HERE.parent/'kernel446/focus-validation.json'")
exec(compile(source,str(HERE/'check-runtime-inputs.py'),'exec'))
