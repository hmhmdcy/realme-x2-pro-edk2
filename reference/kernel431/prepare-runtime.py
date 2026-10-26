"""Reuse the verified reversible module worker with the production auto client."""
from pathlib import Path
import ast,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'build-validation.json').read_text())['passed']
assert json.loads((HERE/'ipa-validation.json').read_text())['passed']
assert json.loads((HERE/'transition-build-validation.json').read_text())['passed']
source=(HERE.parent/'kernel430/prepare-runtime.py').read_text()
source=source.replace("(HERE/'runtime-validation.json')","(HERE.parent/'kernel430/runtime-validation.json')")
a=source.index("probe=json.loads(");z=source.index("assert build['attempt']",a);source=source[:a]+source[z:]
a=source.index("body=body[:a]+''' import fcntl");z=source.index("'''+body[z:]",a)+len("'''+body[z:]")
source=source[:a]+"body=body[:a]+(HERE/'auto-worker-body.py').read_text()+body[z:]"+source[z:]
a=source.index("files={'worker.py'");z=source.index("proof={'modules'",a)
source=source[:a]+'''files={'worker.py':P/'runtime-worker.py','capture':P.parent/'kernel423/capture','pipeline-fixture':P.parent/'kernel363/pipeline-fixture','factory-s5kgw1-private.yaml':P/'factory-s5kgw1-private.yaml',
 'lib/libcamera.so.0.7.2':P/'libcamera.so.0.7.2','ipa/ipa_camss_vfe.so':P/'ipa_camss_vfe.so','ipa/ipa_camss_vfe.so.sign':P/'ipa_camss_vfe.so.sign','proxy/camss_ipa_proxy':P/'camss_ipa_proxy','transition-ipe':P/'transition-ipe'}
for n in ['full-private.bin','pd10-private.bin','parameters-private.bin']:files[n]=P.parent/'kernel430/runtime-collected-r2/replay'/n
'''+source[z:]
source=source.replace("with (root/m.name).open('xb') as f:","p=root/m.name;p.parent.mkdir(parents=True,exist_ok=True)\n with p.open('xb') as f:")
source=source.replace("(root/'pd10-ipe').chmod(0o700)","for n in ['capture','pipeline-fixture','proxy/camss_ipa_proxy','transition-ipe']:(root/n).chmod(0o700)\n(root/'lib/libcamera.so.0.7').symlink_to('libcamera.so.0.7.2')")
source=source.replace("'stage':430","'stage':431").replace('k430-dc-topology-','k431-pd10-auto-')
ast.parse(source);(P/'prepare-runtime-generated.py').write_text(source)
exec(compile(source,str(HERE/'prepare-runtime.py'),'exec'))
