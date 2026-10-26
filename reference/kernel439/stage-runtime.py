from pathlib import Path
import hashlib,json,shutil
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
capture=json.loads((HERE.parent/'kernel437/capture-validation.json').read_text());original=P.parent/'kernel437/capture'
assert hashlib.sha256(original.read_bytes()).hexdigest()==capture['binary_sha256'];shutil.copyfile(original,P/'capture')
capture.update(stage=439,reused_capture_from_stage437=True);(HERE/'capture-validation.json').write_text(json.dumps(capture,indent=2)+'\n')
replay=json.loads((HERE/'replay-build-validation.json').read_text());assert replay['passed'] and hashlib.sha256((P/'tone-replay').read_bytes()).hexdigest()==replay['binary_sha256']
source=(HERE.parent/'kernel435/stage-runtime.py').read_text()
source=source.replace("['ipa','history','native-gtm','profile-export','preflight','source','retention']", "['ipa','front-profile','front-math','front-module','preflight','source','colour-math','replay-build']")
source=source.replace("'stage':435","'stage':439").replace('k435-gtm-auto-','k439-front-colour-')
source=source.replace("P.parent/'kernel423/capture'","P/'capture'")
source=source.replace("'baseline-private.json':P/'preflight-stdout-private.json'", "'baseline-private.json':P/'preflight-stdout-private.json','factory-imx471-private.yaml':P/'factory-imx471-private.yaml','tone-replay':P/'tone-replay'")
source=source.replace("['capture','pipeline-fixture','proxy/camss_ipa_proxy']", "['capture','pipeline-fixture','proxy/camss_ipa_proxy','tone-replay']")
exec(compile(source,str(HERE/'stage-runtime.py'),'exec'))
