from pathlib import Path
import hashlib,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'capture-validation.json').read_text())['binary_sha256']==hashlib.sha256((P/'capture').read_bytes()).hexdigest()
source=(HERE.parent/'kernel436/stage-runtime.py').read_text()
build=json.loads((HERE/'build-validation.json').read_text())
if not build.get('reused_unchanged_runtime_stage436'):
 assert json.loads((HERE/'ipa-validation.json').read_text())['passed']
 proof=json.loads((HERE/'awb-module-validation.json').read_text());assert proof['passed'] and proof['actual_ipa_sha256']==hashlib.sha256((P/'ipa_camss_vfe.so').read_bytes()).hexdigest()
 source=source.replace("for name in ['ipa_camss_vfe.so','ipa_camss_vfe.so.sign','camss_ipa_proxy']:","for name in ['camss_ipa_proxy']:")
 source=source.replace("(HERE.parent/'kernel435/ipa-validation.json')","(HERE/'awb-module-validation.json')")
source=source.replace("shutil.copyfile(P.parent/'kernel435/factory-s5kgw1-private.yaml',P/'factory-s5kgw1-private.yaml')", "shutil.copyfile(P.parent/'kernel436/bls-corrected-s5kgw1-private.yaml',P/'factory-s5kgw1-private.yaml')")
source=source.replace("source=source.replace(\"'stage':435\",\"'stage':436\").replace('k435-gtm-auto-','k436-tone-domain-')", "source=source.replace(\"'stage':435\",\"'stage':437\").replace('k435-gtm-auto-','k437-awb-history-')\nsource=source.replace(\"P.parent/'kernel423/capture'\",\"P/'capture'\")")
exec(compile(source,str(HERE/'stage-runtime.py'),'exec'))
