from pathlib import Path
import hashlib,json,sys
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
assert json.loads((HERE/'lifecycle-validation.json').read_text())['passed']
body=(HERE/'capture-body.py').read_text()
body=body.replace("[('user-native',False,False),('user-isolated',True,False),('user-sustained-1080',True,True)]", "[('user-cancel-1080',True,True),('user-sustained-1080',True,True)]")
body=body.replace("+['factory-s5kgw1-private.yaml','lifecycle','gst-sustained']", "+['factory-s5kgw1-private.yaml','gst-sustained']")
body=body.replace("GST_TARGET_FRAMES='9000'", "PIPELINE_FIXTURE_TIMEOUT_SECONDS=('6' if name=='user-cancel-1080' else '350'),GST_TARGET_FRAMES='9000'")
body=body.replace("timeout=370 if sustained else 100", "timeout=30 if name=='user-cancel-1080' else 370")
body=body.replace("assert code==0 and 'FIXTURE_RESTORATION result=0' in text", "assert code==(1 if name=='user-cancel-1080' else 0) and 'FIXTURE_RESTORATION result=0' in text")
body=body.replace("assert 'GST_RESULT frames=9000 width=1920 height=1080 bus-errors=0 result=0' in text\n    summary['frames']=9000;state['sustained'][name]=summary", """results=re.findall(r'GST_RESULT frames=(\\d+) width=1920 height=1080 bus-errors=0 result=(\\d+)',text);assert len(results)==1
    frames,result=map(int,results[0]);cancel=name=='user-cancel-1080'
    assert (result==9 and 0<frames<9000 and 'exited=1 exit=9 signalled=0' in text) if cancel else (result==0 and frames==9000)
    summary.update(frames=frames,intentional_cancellation=cancel,fixture_timeout_seconds=6 if cancel else 350);state['sustained'][name]=summary""")
body=body.replace("assert summary['frames']<=summary['ipe_completed']<=summary['frames']+(1 if sustained else 3)", "assert summary['frames']<=summary['ipe_completed']")
(HERE/'capture-body-long.py').write_text(body)
source=(HERE.parent/'kernel441/stage-runtime.py').read_text().replace("'stage':441","'stage':449").replace('stage=441','stage=449').replace('k441-variable-pd10-','k449-lifecycle-user-')
source=source.replace("(HERE/(name+'-validation.json'))", "((HERE/'long-client-build-validation.json') if name=='client-build' else ((HERE if name in ['preflight','runtime-inputs'] else HERE.parent/('kernel448' if name=='reentry' else 'kernel442'))/(name+'-validation.json')))")
source=source.replace("HERE/'intree-build-validation.json'", "HERE.parent/'kernel441/intree-build-validation.json'")
source=source.replace("HERE/'build-validation.json'", "HERE.parent/'kernel448/build-validation.json'").replace("userspace['private_ipa_version']==5", "userspace['private_ipa_version']==6").replace("HERE/'auto-capture-body.py'", "HERE/'capture-body-long.py'")
source=source.replace("P.parent/'kernel440/factory-s5kgw1-private.yaml'", "P.parent/'kernel443/factory-s5kgw1-private.yaml'")
source=source.replace("for n in ['capture','pd10-ipe']:files[n]=P/n", "files['gst-sustained']=P/'gst-sustained';files['pipeline-fixture']=P/'pipeline-fixture-long';files['user-launcher.py']=HERE/'user-launcher.py';files['conditions-observer.py']=HERE/'conditions-observer.py'")
source=source.replace("HERE/'client-build-validation.json'", "HERE/'long-client-build-validation.json'")
source=source.replace("['capture','pd10-ipe','pipeline-fixture','proxy/camss_ipa_proxy']", "['gst-sustained','pipeline-fixture','user-launcher.py','proxy/camss_ipa_proxy']")
exec(compile(source,str(HERE/'stage-long-runtime.py'),'exec'))
attempt=sys.argv[1];p=HERE/f'runtime-staging-{attempt}-validation.json';r=json.loads(p.read_text())
r.update(core_sha256=inputs['lib/libcamera.so.0.7.2']['sha256'],profile_sha256=hashlib.sha256((P.parent/'kernel443/factory-s5kgw1-private.yaml').read_bytes()).hexdigest(),private_ipa_version=6,reused448_without_changes=True,uid10000_zero_capability_consumers=True,fixture_timeout_seconds=350,gst_graceful_signal_cleanup=True,lifecycle_rows_reused_from_ended_r1=True)
p.write_text(json.dumps(r,indent=2)+'\n')
