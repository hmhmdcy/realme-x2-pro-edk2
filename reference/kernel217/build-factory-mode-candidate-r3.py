from pathlib import Path
here=Path(__file__).resolve().parent
source=(here/'build-factory-mode-candidate-r2.py').read_text().replace('candidate-build-r2','candidate-build-r3')
exec(compile(source,'candidate-build-final-source-r3','exec'))
