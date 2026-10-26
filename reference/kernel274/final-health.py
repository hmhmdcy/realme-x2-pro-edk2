from pathlib import Path
R=Path(__file__).resolve().parent
source=(R.parent/'kernel273/final-health.py').read_text().replace('stage=273','stage=274')
exec(compile(source,'final-health274-derived.py','exec'),dict(__file__=str(R/'final-health.py')))
