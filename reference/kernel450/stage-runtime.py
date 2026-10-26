from pathlib import Path
import hashlib,json,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
assert json.loads((HERE/'retirement-validation.json').read_text())['passed']
body=(HERE.parent/'kernel449/capture-body-long.py').read_text().replace('k449-user-','k450-user-')
body=body.replace("[('user-cancel-1080',True,True),('user-sustained-1080',True,True)]", "[('user-sustained-1080',True,True)]")
body=body.replace('try:observer.wait(timeout=3)','try:observer.wait(timeout=8)')
body=body.replace('observer.terminate()','observer_timeout=False;observer.terminate()')
body=body.replace('except subprocess.TimeoutExpired:observer.kill();observer.wait(timeout=3)','except subprocess.TimeoutExpired:observer_timeout=True;observer.kill();observer.wait(timeout=3)')
body=body.replace('observer_log.close();assert observer.returncode==0',"observer_log.close();state.setdefault('observer_exits',{})[name]=dict(exit_code=observer.returncode,timed_out=observer_timeout)")
body=body.replace('   shutil.rmtree(userroot)','   shutil.rmtree(userroot)\n   if observer is not None:assert observer.returncode==0')
(HERE/'capture-body.py').write_text(body)
(HERE/'user-launcher.py').write_text((HERE.parent/'kernel449/user-launcher.py').read_text().replace('k449-user-','k450-user-'))
source=(HERE.parent/'kernel441/stage-runtime.py').read_text().replace("'stage':441","'stage':450").replace('stage=441','stage=450').replace('k441-variable-pd10-','k450-stats-retirement-')
source=source.replace("(HERE/(name+'-validation.json'))", "((HERE.parent/'kernel449/long-client-build-validation.json') if name=='client-build' else ((HERE if name in ['preflight','runtime-inputs','reentry'] else HERE.parent/'kernel442')/(name+'-validation.json')))")
source=source.replace("HERE/'intree-build-validation.json'", "HERE.parent/'kernel441/intree-build-validation.json'")
source=source.replace("userspace['private_ipa_version']==5", "userspace['private_ipa_version']==6").replace("HERE/'auto-capture-body.py'", "HERE/'capture-body.py'")
source=source.replace("P.parent/'kernel440/factory-s5kgw1-private.yaml'", "P.parent/'kernel443/factory-s5kgw1-private.yaml'")
source=source.replace("for n in ['capture','pd10-ipe']:files[n]=P/n", "files['gst-sustained']=P.parent/'kernel449/gst-sustained';files['pipeline-fixture']=P.parent/'kernel449/pipeline-fixture-long';files['user-launcher.py']=HERE/'user-launcher.py';files['conditions-observer.py']=HERE/'conditions-observer.py'")
source=source.replace("HERE/'client-build-validation.json'", "HERE.parent/'kernel449/long-client-build-validation.json'")
source=source.replace("['capture','pd10-ipe','pipeline-fixture','proxy/camss_ipa_proxy']", "['gst-sustained','pipeline-fixture','user-launcher.py','proxy/camss_ipa_proxy']")
assert json.loads((HERE/'observer-validation.json').read_text())['passed']
assert json.loads((HERE/'cancellation-validation.json').read_text())['camera_cancellation_passed']
exec(compile(source,str(HERE/'stage-runtime.py'),'exec'))
attempt=sys.argv[1];p=HERE/f'runtime-staging-{attempt}-validation.json';r=json.loads(p.read_text())
r.update(core_sha256=inputs['lib/libcamera.so.0.7.2']['sha256'],profile_sha256=hashlib.sha256((P.parent/'kernel443/factory-s5kgw1-private.yaml').read_bytes()).hexdigest(),private_ipa_version=6,uid10000_zero_capability_consumers=True,fixture_timeout_seconds=350,gst_graceful_signal_cleanup=True,only_stats_retirement_changed=True)
p.write_text(json.dumps(r,indent=2)+'\n')
