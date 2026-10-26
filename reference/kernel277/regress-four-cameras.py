from pathlib import Path
import json
R=Path(__file__).resolve().parent
assert json.loads((R/'focus-metadata-r1-validation.json').read_text())['error'] is None
services=json.loads((R/'services-validation.json').read_text());assert services['services']['greetd']['exit']==0
source=(R.parent/'kernel273/regress-four-cameras.py').read_text();prefix=source[source.index('text='):source.index('exec(compile')]
ns=dict(R=R.parent/'kernel273');exec(compile(prefix,'resolve-four-camera-template','exec'),ns)
text=ns['text'].replace('k273','k277').replace('k277-work','k276-work').replace('stage=273','stage=277')
exec(compile(text,'four-camera-regression276-derived.py','exec'),dict(__file__=str(R/'four-camera-regression-generated.py')))
