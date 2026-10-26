"""Reuse the guarded temporary module transaction with the candidate library."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
body=(HERE.parent/'kernel417/runtime-worker-body.py').read_text()
start=body.index(" launch([str(root/'request-client')")
end=body.index(" unload();load('normal');restored=True;",start)
middle=r''' library=root/'lib';library.mkdir();(library/'libcamera.so.0.7.2').write_bytes((root/'libcamera.so.0.7.2').read_bytes());(library/'libcamera.so.0.7').symlink_to('libcamera.so.0.7.2')
 env=os.environ.copy()
 for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(n,None)
 env.update(LD_LIBRARY_PATH=str(library),LIBCAMERA_IPA_MODULE_PATH='/usr/lib/libcamera/ipa',LIBCAMERA_IPA_PROXY_PATH='/usr/libexec/libcamera',LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
 launch([str(root/'ipe-smoke'),'/dev/'+nodes[0].name,media[0],str(root)],'wrapper-pixels',env=env,timeout=90)
 rows=[json.loads(l) for l in (root/'wrapper-pixels.out').read_text().splitlines()]
 frames=[r for r in rows if 'sequence' in r]
 assert len(rows)==19 and [(r['case'],r['sequence'],r['mode']) for r in frames]==[(c,s,m) for c in range(2) for s,m in enumerate([0,1,2,2,3,4,0,1])]
 assert rows[-1]['actual_libcamera_wrapper'] and rows[-1]['frames']==16 and rows[-1]['cancelled']==4 and rows[-1]['passed']
 state['native_cases']=rows;state['after_native']=idle();owner_zero();s=state['after_native']
 assert s['completed']>=16 and s['completed']+s['cancelled']==s['jobs']<=20 and s['direct_completed']==s['completed']
 assert not any(s[k] for k in ['failed','first_error']) and not core()['watchdogs'] and not core()['protocol_errors']
 save('wrapper-request-pixels-and-cancellation-complete')
 captures={}
 def accepted(label,text,previous,frames,expect_ipe=True):
  assert 'FIXTURE_RESTORATION result=0' in text
  assert ('IPE enabled ' in text)==expect_ipe
  if expect_ipe:assert re.search(r'IPE enabled .* requests=1',text)
  after=idle();owner_zero();delta={k:after[k]-previous[k] for k in ['jobs','completed','direct_completed','cancelled']}
  assert delta['jobs']==delta['completed']+delta['cancelled'] and delta['completed']==delta['direct_completed']
  assert (delta['completed']>=frames>0) if expect_ipe else delta['jobs']==0
  assert not any(after[k] for k in ['failed','first_error']) and not core()['watchdogs'] and not core()['protocol_errors']
  captures[label]=dict(frames=frames,ipe=delta,requests_enabled=expect_ipe,passed=True)
  state['candidate_captures']=captures.copy();save('candidate-'+label)
 for model in ['imx471','imx319','s5k3m5','s5kgw1']:
  device=next(p for p in Path('/sys/bus/i2c/drivers',model).iterdir() if (p/'of_node').exists());identity='/base'+str((device/'of_node').resolve()).split('/base',1)[1];before=m2m()
  text=launch([str(root/'pipeline-fixture'),'/dev/media0','/var/lib/samurai/k362-install-r1/bin/gst-hardware-probe',identity,'640','480'],'candidate-gst-'+model,env=env,timeout=45)
  match=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',text);assert match and int(match[1])>0 and int(match[4])==int(match[5])==0
  accepted(model,text,before,int(match[1]))
 for kind in ['dual','raw']:
  before=m2m();text=launch([str(root/'pipeline-fixture'),'/dev/media0',str(root/'pipeline-smoke'),'s5kgw1@4608x3456',kind],'candidate-'+kind,env=env,timeout=45)
  assert 'failed=0 result=0' in text
  pairs=re.findall(r'RawPair .* matched=(\d+)',text);assert pairs and all(v=='1' for v in pairs)
  frames=len(re.findall(r'RAW_IMAGE request=\d+ format=NV12',text))
  accepted(kind,text,before,frames,expect_ipe=kind=='dual')
  captures[kind]['raw_pairs']=len(pairs)
 nodes_main=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith('s5kgw1 ')];assert len(nodes_main)==1
 isolated=dict(env,LIBCAMERA_IPA_FORCE_ISOLATION='1');before=m2m()
 text=launch([str(root/'pipeline-fixture'),'/dev/media0','/var/lib/samurai/k362-install-r1/bin/adaptation-smoke','s5kgw1','/dev/'+nodes_main[0].name,'4608x3456','2'],'candidate-isolated',env=isolated,timeout=60)
 app=re.findall(r'ADAPT_PID value=(\d+)',text);ipa=set(re.findall(r'IPA stats pid=(\d+)',text))
 assert len(app)==1 and ipa and all(v!=app[0] for v in ipa)
 assert ' failed=0 result=0' in text and text.count('ADAPT_PHASE ')==5 and text.count('GAMMA_APPLIED ')==1
 accepted('isolated',text,before,text.count('ADAPT_FRAME '));captures['isolated']['actual_isolation_verified']=True
 state['candidate_captures']=captures.copy();state['candidate_after']=idle();owner_zero()
 save('candidate-libcamera-request-suite-complete')
'''
body=body[:start]+middle+body[end:]
body=body.replace('known_warning_from_failed_runtime_r2=True','known_warning_from417_failed_runtime_r2=True')
ast.parse(body);(HERE/'runtime-worker-body.py').write_text(body)
stage=(HERE.parent/'kernel417/stage-runtime.py').read_text()
stage=stage.replace("(HERE/'intree-build-validation.json')","(HERE.parent/'kernel417/intree-build-validation.json')")
stage=stage.replace("assert json.loads((HERE/'params-validation.json').read_text())['passed']","assert json.loads((HERE/'ipe-validation.json').read_text())['passed']")
stage=stage.replace("assert json.loads((HERE/'client-build-validation.json').read_text())['passed']","assert json.loads((HERE/'runtime-build-validation.json').read_text())['passed']")
stage=stage.replace('stage=417','stage=418').replace("'stage':417","'stage':418").replace('k417-request-r4','k418-libcamera-r2').replace('payload-r4-private','payload-r2-private')
stage=stage.replace("'request-client':P/'request-client'","'ipe-smoke':P/'ipe-smoke','libcamera.so.0.7.2':P/'libcamera.so.0.7.2','pipeline-smoke':P.parent/'kernel387/pipeline-smoke'")
stage=stage.replace("['pipeline-fixture','request-client']","['pipeline-fixture','ipe-smoke','pipeline-smoke']")
# Check the previous completed transaction's actual process before switching.
needle="root.mkdir(mode=0o700);print(json.dumps"
replacement="""prior=Path('/var/lib/samurai/k418-libcamera-r1');s=json.loads((prior/'state.json').read_text());assert s['terminal'] and s['normal395_restored']
for key in ['pid','client_pid','collector_pid']:
 p=Path('/proc',str(s.get(key,-1)))
 try:assert (p/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z' or str(prior).encode() not in (p/'cmdline').read_bytes()
 except FileNotFoundError:pass
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
root.mkdir(mode=0o700);print(json.dumps"""
assert stage.count(needle)==1;stage=stage.replace(needle,replacement)
ast.parse(stage);(HERE/'stage-runtime.py').write_text(stage)
runtime=(HERE.parent/'kernel417/runtime.py').read_text().replace('stage=417','stage=418').replace('k417-request-r4','k418-libcamera-r2').replace('runtime-collected-r4','runtime-collected-r2').replace("['request-client','pipeline-fixture']","['ipe-smoke','pipeline-fixture','pipeline-smoke']")
ast.parse(runtime);(HERE/'runtime.py').write_text(runtime)
print('Prepared candidate library/wrapper, camera requests, cancellation and formal restoration transaction.')
