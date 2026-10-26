"""Stage IPA6 as one matched cohort, retaining the 443 profile/probe/kernel."""
from pathlib import Path
import hashlib,json,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
assert json.loads((HERE/'focused-module-validation.json').read_text())['passed']
body=(HERE.parent/'kernel443/gst-capture-body.py').read_text()
marker="   idle();s=status();summary['ipe_completed']=s['completed']-before"
extra='''   focused=re.findall(r'FRAME_IPA_PREPARE epoch=1 sof=(\\d+) combined=(\\d+) focus-us=(\\d+) dispatch-us=(\\d+) focus-status=(-?\\d+) tone-prepared=(\\d+)',text)
   assert len(focused)>=summary['frames'] and all(r[1]=='1' and r[4]=='0' and r[5]=='1' for r in focused)
   summary['combined_focus_tone_calls']=len(focused)
'''
assert body.count(marker)==1;body=body.replace(marker,extra+marker)
(HERE/'gst-capture-body.py').write_text(body)
source=(HERE.parent/'kernel441/stage-runtime.py').read_text().replace("'stage':441","'stage':444").replace('stage=441','stage=444').replace('k441-variable-pd10-','k444-focused-gst-')
source=source.replace("(HERE/(name+'-validation.json'))", "((HERE if name in ['preflight','runtime-inputs','reentry'] else HERE.parent/('kernel443' if name=='client-build' else 'kernel442'))/(name+'-validation.json'))")
source=source.replace("HERE/'intree-build-validation.json'", "HERE.parent/'kernel441/intree-build-validation.json'")
source=source.replace("userspace['private_ipa_version']==5", "userspace['private_ipa_version']==6")
source=source.replace("HERE/'auto-capture-body.py'", "HERE/'gst-capture-body.py'")
source=source.replace("P.parent/'kernel440/factory-s5kgw1-private.yaml'", "P.parent/'kernel443/factory-s5kgw1-private.yaml'")
source=source.replace("for n in ['capture','pd10-ipe']:files[n]=P/n", "for n in ['gst-hardware-probe']:files[n]=P.parent/'kernel443'/n")
source=source.replace("HERE/'client-build-validation.json'", "HERE.parent/'kernel443/client-build-validation.json'")
source=source.replace("['capture','pd10-ipe','pipeline-fixture','proxy/camss_ipa_proxy']", "['gst-hardware-probe','pipeline-fixture','proxy/camss_ipa_proxy']")
exec(compile(source,str(HERE/'stage-runtime.py'),'exec'))
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1';p=HERE/f'runtime-staging-{attempt}-validation.json';r=json.loads(p.read_text())
r.update(core_sha256=inputs['lib/libcamera.so.0.7.2']['sha256'],profile_sha256=hashlib.sha256((P.parent/'kernel443/factory-s5kgw1-private.yaml').read_bytes()).hexdigest(),probe_sha256=json.loads((HERE.parent/'kernel443/client-build-validation.json').read_text())['clients'][0]['sha256'],private_ipa_version=6)
p.write_text(json.dumps(r,indent=2)+'\n')
