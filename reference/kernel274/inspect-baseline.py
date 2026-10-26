from pathlib import Path
R=Path(__file__).resolve().parent
text=(R.parent/'kernel273/final-health.py').read_text().replace("host.PRIVATE/'final-health-private.json'","host.PRIVATE/'baseline-health-private.json'").replace("R/'final-health-validation.json'","R/'baseline-health-validation.json'")
text=text.replace('stage=273','stage=274')
exec(compile(text,'baseline274-generated.py','exec'),dict(__file__=str(R/'baseline-generated.py')))
