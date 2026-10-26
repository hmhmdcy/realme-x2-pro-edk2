from pathlib import Path
import hashlib,json,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
source=(HERE.parent/'kernel441/stage-runtime.py').read_text().replace("'stage':441","'stage':449").replace('stage=441','stage=449').replace('k441-variable-pd10-','k449-lifecycle-user-')
source=source.replace("(HERE/(name+'-validation.json'))", "((HERE if name in ['preflight','runtime-inputs','client-build'] else HERE.parent/('kernel448' if name=='reentry' else 'kernel442'))/(name+'-validation.json'))")
source=source.replace("HERE/'intree-build-validation.json'", "HERE.parent/'kernel441/intree-build-validation.json'")
source=source.replace("HERE/'build-validation.json'", "HERE.parent/'kernel448/build-validation.json'").replace("userspace['private_ipa_version']==5", "userspace['private_ipa_version']==6").replace("HERE/'auto-capture-body.py'", "HERE/'capture-body.py'")
source=source.replace("P.parent/'kernel440/factory-s5kgw1-private.yaml'", "P.parent/'kernel443/factory-s5kgw1-private.yaml'")
source=source.replace("for n in ['capture','pd10-ipe']:files[n]=P/n", "for n in ['lifecycle','gst-sustained']:files[n]=P/n\nfiles['user-launcher.py']=HERE/'user-launcher.py';files['conditions-observer.py']=HERE/'conditions-observer.py'")
source=source.replace("['capture','pd10-ipe','pipeline-fixture','proxy/camss_ipa_proxy']", "['lifecycle','gst-sustained','user-launcher.py','pipeline-fixture','proxy/camss_ipa_proxy']")
exec(compile(source,str(HERE/'stage-runtime.py'),'exec'))
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';p=HERE/f'runtime-staging-{attempt}-validation.json';r=json.loads(p.read_text())
r.update(core_sha256=inputs['lib/libcamera.so.0.7.2']['sha256'],profile_sha256=hashlib.sha256((P.parent/'kernel443/factory-s5kgw1-private.yaml').read_bytes()).hexdigest(),private_ipa_version=6,reused448_without_changes=True,uid10000_zero_capability_consumers=True)
p.write_text(json.dumps(r,indent=2)+'\n')
