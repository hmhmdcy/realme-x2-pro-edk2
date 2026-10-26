"""Repeat native multi-sensor switching on the newly installed paired stack."""
from pathlib import Path
import json
R=Path(__file__).resolve().parent
assert json.loads((R/'fractional-manual-r1-validation.json').read_text())['exit']==0
text=(R.parent/'kernel270/regress-three-cameras.py').read_text()
text=text.replace('k270-three-camera-regression-r1','k271-three-camera-regression-r1').replace('stage=270','stage=271')
exec(compile(text,'three-camera-regression-generated.py','exec'),dict(__file__=str(R/'three-camera-regression-generated.py')))
