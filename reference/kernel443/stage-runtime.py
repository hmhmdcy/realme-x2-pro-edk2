"""Stage unchanged 442 code/modules plus the stock mode4 profile and GST probe."""
from pathlib import Path
import hashlib,json,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
assert json.loads((HERE/'profile-module-validation.json').read_text())['passed']
inputs=json.loads((P.parent/'kernel442/runtime-input-files-private.json').read_text())
inputs={k:v for k,v in inputs.items() if k.startswith(('lib/','ipa/','proxy/'))}
for row in inputs.values():assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
(P/'runtime-input-files-private.json').write_text(json.dumps(inputs,indent=2)+'\n')
source=(HERE.parent/'kernel441/stage-runtime.py').read_text()
source=source.replace("'stage':441","'stage':443").replace('stage=441','stage=443').replace('k441-variable-pd10-','k443-gst-consumer-')
source=source.replace("(HERE/(name+'-validation.json'))", "((HERE if name in ['preflight','client-build'] else HERE.parent/'kernel442')/(name+'-validation.json'))")
source=source.replace("HERE/'intree-build-validation.json'", "HERE.parent/'kernel441/intree-build-validation.json'")
source=source.replace("HERE/'build-validation.json'", "HERE.parent/'kernel442/build-validation.json'")
source=source.replace("HERE/'auto-capture-body.py'", "HERE/'gst-capture-body.py'")
source=source.replace("P.parent/'kernel440/factory-s5kgw1-private.yaml'", "P/'factory-s5kgw1-private.yaml'")
source=source.replace("for n in ['capture','pd10-ipe']:", "for n in ['gst-hardware-probe']:")
source=source.replace("['capture','pd10-ipe','pipeline-fixture','proxy/camss_ipa_proxy']", "['gst-hardware-probe','pipeline-fixture','proxy/camss_ipa_proxy']")
exec(compile(source,str(HERE/'stage-runtime.py'),'exec'))
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';p=HERE/f'runtime-staging-{attempt}-validation.json';r=json.loads(p.read_text())
r.update(core_sha256=inputs['lib/libcamera.so.0.7.2']['sha256'],profile_sha256=hashlib.sha256((P/'factory-s5kgw1-private.yaml').read_bytes()).hexdigest(),probe_sha256=json.loads((HERE/'client-build-validation.json').read_text())['clients'][0]['sha256'],private_ipa_version=5)
p.write_text(json.dumps(r,indent=2)+'\n')
