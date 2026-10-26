from pathlib import Path
R=Path(__file__).resolve().parent
source=(R.parent/'kernel273/inspect-services.py').read_text().replace('stage=273','stage=275')
exec(compile(source,'services275-derived.py','exec'),dict(__file__=str(R/'inspect-services.py')))
