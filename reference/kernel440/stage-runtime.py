from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
capture=json.loads((HERE/'capture-validation.json').read_text());assert hashlib.sha256((P/'capture').read_bytes()).hexdigest()==capture['binary_sha256']
assert json.loads((HERE/'build-validation.json').read_text())['attempt']==2
assert json.loads((HERE/'packaged-contract-validation.json').read_text())['build_iteration']==2
source=(HERE.parent/'kernel435/stage-runtime.py').read_text()
source=source.replace("['ipa','history','native-gtm','profile-export','preflight','source','retention']", "['packaged-contract','package-artifact','preflight','source','initial-state']")
source=source.replace("'stage':435","'stage':440").replace('k435-gtm-auto-','k440-packaged-cohort-').replace("P.parent/'kernel423/capture'","P/'capture'")
source=source.replace("'baseline-private.json':P/'preflight-stdout-private.json'", "'baseline-private.json':P/'preflight-stdout-private.json','pipeline-smoke':P/'pipeline-smoke','factory-imx319-private.yaml':P/'factory-imx319-private.yaml','factory-s5k3m5-private.yaml':P/'factory-s5k3m5-private.yaml','factory-imx471-private.yaml':P/'factory-imx471-private.yaml'")
source=source.replace("['libcamera.so.0.7.2','ipa_camss_vfe.so'", "['libcamera-base.so.0.7.2','libcamera.so.0.7.2','ipa_camss_vfe.so'")
source=source.replace("['capture','pipeline-fixture','proxy/camss_ipa_proxy']", "['capture','pipeline-fixture','pipeline-smoke','proxy/camss_ipa_proxy']")
source=source.replace("(root/'lib/libcamera.so.0.7').symlink_to('libcamera.so.0.7.2')", "(root/'lib/libcamera.so.0.7').symlink_to('libcamera.so.0.7.2')\n(root/'lib/libcamera-base.so.0.7').symlink_to('libcamera-base.so.0.7.2')")
exec(compile(source,str(HERE/'stage-runtime.py'),'exec'))
