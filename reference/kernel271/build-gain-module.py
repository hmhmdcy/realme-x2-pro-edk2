"""Build the reviewed sensor target against Image183; restore the canonical tree."""
from pathlib import Path

R=Path(__file__).resolve().parent
text=(R.parent/'kernel270/build-current-module.py').read_text()
text=text.replace("kernel270')", "kernel271')").replace('stage=270','stage=271')
assert "kernel271')" in text
exec(compile(text,'build-gain-module-generated.py','exec'),dict(__file__=str(R/'build-gain-module-generated.py')))
