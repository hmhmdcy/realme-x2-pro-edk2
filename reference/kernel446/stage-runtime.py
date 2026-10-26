"""Stage one fresh transaction, with the existing bounded restoration worker."""
from pathlib import Path
import hashlib,json,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
focus=json.loads((HERE/'focus-validation.json').read_text());af=json.loads((HERE/'af-client-build-validation.json').read_text())
assert focus['passed'] and af['passed']
assert hashlib.sha256((P/'focus-bench').read_bytes()).hexdigest()==focus['benchmark_sha256']
gst=(HERE.parent/'kernel444/gst-capture-body.py').read_text().replace('for isolated in [False,True]:','for isolated in [True]:')
end=" state['candidate_final_status']=status();state['candidate_final_core']=core();verified=True\n"
assert gst.count(end)==1;gst=gst.replace(end,'')
body=(HERE.parent/'kernel445/benchmark-body.py').read_text()+gst+(HERE/'extra-capture-body.py').read_text()+(HERE.parent/'kernel442/compatibility-body.py').read_text()+end
(HERE/'capture-body.py').write_text(body)
source=(HERE.parent/'kernel441/stage-runtime.py').read_text().replace("'stage':441","'stage':446").replace('stage=441','stage=446').replace('k441-variable-pd10-','k446-focus-workspace-')
source=source.replace("(HERE/(name+'-validation.json'))", "((HERE if name in ['preflight','runtime-inputs','reentry'] else HERE.parent/('kernel443' if name=='client-build' else 'kernel442'))/(name+'-validation.json'))")
source=source.replace("HERE/'intree-build-validation.json'", "HERE.parent/'kernel441/intree-build-validation.json'").replace("userspace['private_ipa_version']==5", "userspace['private_ipa_version']==6").replace("HERE/'auto-capture-body.py'", "HERE/'capture-body.py'")
source=source.replace("P.parent/'kernel440/factory-s5kgw1-private.yaml'", "P.parent/'kernel443/factory-s5kgw1-private.yaml'")
source=source.replace("for n in ['capture','pd10-ipe']:files[n]=P/n", """files.update({'gst-hardware-probe':P.parent/'kernel443/gst-hardware-probe','capture':P.parent/'kernel442/capture','af-capture':P/'af-capture','pipeline-smoke':P.parent/'kernel440/pipeline-smoke','focus-bench':P/'focus-bench','focus-fixtures-private.json':P/'focus-fixtures-private.json'})
for model,row in json.loads((P/'extra-profiles-private.json').read_text()).items():
 p=Path(row['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'];files['factory-'+model+'-private.yaml']=p
for row in af['clients']:assert hashlib.sha256(files[row['name']].read_bytes()).hexdigest()==row['sha256']
assert hashlib.sha256(files['capture'].read_bytes()).hexdigest()=='052cdeb9aa7d1b6c4140067ccd45604fdddc9dc4f02adf2a5d8b608e9625ffb6'
assert hashlib.sha256(files['pipeline-smoke'].read_bytes()).hexdigest()=='0d692025b2adaf6b5cbadd7fac24ae3034214f5f262ce811061d1a6ea745f4fc'""")
source=source.replace("HERE/'client-build-validation.json'", "HERE.parent/'kernel443/client-build-validation.json'")
source=source.replace("['capture','pd10-ipe','pipeline-fixture','proxy/camss_ipa_proxy']", "['capture','af-capture','gst-hardware-probe','pipeline-smoke','focus-bench','pipeline-fixture','proxy/camss_ipa_proxy']")
exec(compile(source,str(HERE/'stage-runtime.py'),'exec'))
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';p=HERE/f'runtime-staging-{attempt}-validation.json';r=json.loads(p.read_text())
r.update(core_sha256=inputs['lib/libcamera.so.0.7.2']['sha256'],profile_sha256=hashlib.sha256((P.parent/'kernel443/factory-s5kgw1-private.yaml').read_bytes()).hexdigest(),private_ipa_version=6,other_stock_profiles_reused=True)
p.write_text(json.dumps(r,indent=2)+'\n')
