from pathlib import Path
R=Path(__file__).resolve().parent
source=(R.parent/'kernel273/probe-main.py').read_text().replace('k273','k276').replace('stage=273','stage=276')
exec(compile(source,'main276-derived.py','exec'),dict(__file__=str(R/'probe-main.py')))
