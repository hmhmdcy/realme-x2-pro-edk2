"""Use the exact 441 candidate with one instrumented 720p isolated capture."""
from pathlib import Path
import hashlib,json,shutil,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
mode=sys.argv[2] if len(sys.argv)>2 else 'queued'
assert mode in ['queued','direct-delay','queued-delay','direct-long','queued-long','full']
queued=not mode.startswith('direct');delay=500 if mode.endswith('long') else 200 if mode.endswith('delay') else 0
sys.argv=sys.argv[:2]
assert json.loads((HERE/'preflight-validation.json').read_text())['passed']
probe=json.loads((HERE/'client-build-validation.json').read_text());assert probe['passed']
for name in ['geometry-contract','format-contract','native-bl','userspace-layout','reentry','aux-restart','intree-build']:
 data=json.loads((HERE.parent/f'kernel441/{name}-validation.json').read_text());assert data['passed'];(HERE/(name+'-validation.json')).write_text(json.dumps(data,indent=2)+'\n')
if not (HERE/'source-state.json').exists():
 for name in ['runtime-inputs','build']:shutil.copyfile(HERE.parent/f'kernel441/{name}-validation.json',HERE/(name+'-validation.json'))
 inputs=json.loads((P.parent/'kernel441/runtime-input-files-private.json').read_text())
else:
 assert json.loads((HERE/'runtime-inputs-validation.json').read_text())['stage']==442
 assert json.loads((HERE/'build-validation.json').read_text())['stage']==442
 inputs=json.loads((P/'runtime-input-files-private.json').read_text())
for row in inputs.values():assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
if mode=='full':
 for name,path in [('pd10-ipe',P.parent/'kernel441/pd10-ipe'),('pipeline-smoke',P.parent/'kernel440/pipeline-smoke')]:inputs[name]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(P/'runtime-input-files-private.json').write_text(json.dumps(inputs,indent=2)+'\n')
body=(HERE.parent/'kernel441/auto-capture-body.py').read_text().replace("diagnostic=(root/'diagnostic.json').exists()",'diagnostic=True').replace('diagnostic and width!=1920','diagnostic and width!=1280')
if mode=='full':
 body=body.replace('diagnostic=True','diagnostic=False')
 marker=" state['candidate_final_status']=status();"
 body=body.replace(marker,(HERE/'compatibility-body.py').read_text()+marker)
body=body.replace("   if isolated:env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'", "   env['CAPTURE_QUEUED']="+repr('1' if queued else '0')+";env['CAPTURE_DELAY_MS']="+repr(str(delay))+"\n   if isolated:env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'")
(HERE/'auto-capture-body.py').write_text(body)
source=(HERE.parent/'kernel441/stage-runtime.py').read_text().replace("'stage':441","'stage':442").replace('stage=441','stage=442').replace('k441-variable-pd10-','k442-callback-timing-')
source=source.replace("for n in ['capture','pd10-ipe']:","for n in ['capture']:")
source=source.replace("['capture','pd10-ipe','pipeline-fixture','proxy/camss_ipa_proxy']", "['capture','pipeline-fixture','proxy/camss_ipa_proxy']")
if mode=='full':source=source.replace("['capture','pipeline-fixture','proxy/camss_ipa_proxy']", "['capture','pd10-ipe','pipeline-smoke','pipeline-fixture','proxy/camss_ipa_proxy']")
exec(compile(source,str(HERE/'stage-runtime.py'),'exec'))
attempt=sys.argv[1] if len(sys.argv)>1 else 'r1'
p=HERE/('runtime-staging-'+attempt+'-validation.json');record=json.loads(p.read_text())
record.update(mode=mode,core_sha256=inputs['lib/libcamera.so.0.7.2']['sha256'],capture_sha256=probe['clients'][0]['sha256'],private_ipa_version=5)
p.write_text(json.dumps(record,indent=2)+'\n')
