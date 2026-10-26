"""Measure the installed native-code/helper pair, not the prior integer ABI."""
from pathlib import Path
import json, sys
R=Path(__file__).resolve().parent
assert json.loads((R/'gain-install-r2-validation.json').read_text())['paired_update_verified']
text=(R/'run-control-baseline.py').read_text()
for a,b in [
 ('/run/samurai-camera271-probes','/run/samurai-camera271-fractional-probes'),
 ('control-probe-build-validation.json','fractional-probe-build-validation.json'),
 ('telephoto-control-probe271','telephoto-fractional-probe271'),
 ("'baseline-'", "'fractional-'"),
 ('baseline-manual-r1-validation.json','fractional-manual-r1-validation.json'),
 ('baseline-settled-r1-validation.json','fractional-settled-r1-validation.json'),
 ('22315c6f3eb233add16e33658bd071dbc973499744b21323adf8b771c1552f72','11791431fb7d50ccd64163fdc5d753b61be5844830e90d14ce4f738a42f8b8f5'),
 ("'telephoto-contr'", "'telephoto-fract'")
]:
    assert a in text,a
    text=text.replace(a,b)
text=text.replace(' time.sleep(1)\n report=dict', ' time.sleep(3)\n report=dict')
exec(compile(text,'fractional-control-generated.py','exec'),dict(__file__=str(R/'fractional-control-generated.py')))
