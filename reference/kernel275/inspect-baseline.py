from pathlib import Path
R=Path(__file__).resolve().parent
source=(R.parent/'kernel273/final-health.py').read_text().replace('stage=273','stage=275')
source=source.replace("host.PRIVATE/'final-health-private.json'","host.PRIVATE/'baseline-health-private.json'").replace("R/'final-health-validation.json'","R/'baseline-health-validation.json'")
exec(compile(source,'baseline275-generated.py','exec'),dict(__file__=str(R/'inspect-baseline.py')))
