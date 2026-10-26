from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'capture-validation.json').read_text())['binary_sha256']==hashlib.sha256((P/'capture').read_bytes()).hexdigest()
source=(HERE.parent/'kernel435/stage-runtime.py').read_text()
source=source.replace("for name in ['ipa','history','native-gtm','profile-export','preflight','source','retention']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']", "for name in ['existing-inventory','rear-profile','rear-math','native-gtm','preflight']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']")
source=source.replace("'stage':435","'stage':438").replace('k435-gtm-auto-','k438-multicamera-tone-')
source=source.replace("P.parent/'kernel423/capture'","P/'capture'")
source=source.replace("'baseline-private.json':P/'preflight-stdout-private.json'", "'baseline-private.json':P/'preflight-stdout-private.json','factory-imx319-private.yaml':P/'factory-imx319-private.yaml','factory-s5k3m5-private.yaml':P/'factory-s5k3m5-private.yaml'")
exec(compile(source,str(HERE/'stage-runtime.py'),'exec'))
