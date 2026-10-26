from pathlib import Path
R=Path(__file__).resolve().parent
source=(R.parent/'kernel275/inspect-lens.py').read_text().replace('stage=275','stage=276')
exec(compile(source,'lens276-derived.py','exec'),dict(__file__=str(R/'inspect-lens.py')))
