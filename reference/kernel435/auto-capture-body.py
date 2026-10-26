 state['captures']={}
 nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith('s5kgw1 ')];assert len(nodes)==1
 for isolated in [False,True]:
  name='scene-isolated' if isolated else 'scene-native';case=root/name;case.mkdir()
  env=dict(os.environ,LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG',CAPTURE_DIR=str(case))
  for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(n,None)
  env.update(LD_LIBRARY_PATH=str(root/'lib'),LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(root/'proxy'),LIBCAMERA_CAMSS_VFE_PROFILE=str(root/'factory-s5kgw1-private.yaml'))
  if isolated:env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'
  before=status()['completed']
  with (case/'client.log').open('xb') as log:
   child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'capture'),'s5kgw1','/dev/'+nodes[0].name,'4608x3456','0'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save('automatic-gtm-'+name,client_pid=child.pid);code=child.wait(timeout=45)
  text=(case/'client.log').read_text(errors='replace')
  state['captures'][name]=dict(exit_code=code,frames=text.count('ADAPT_FRAME '),pd10_ready=text.count('PD10_READY '),gtm_queues=text.count('IFE_GTM_QUEUE '),gtm_applied=text.count('IFE_GTM_APPLIED '),tone_prepares=text.count('IPE_TONE_PREPARE '),tone_receipts=text.count('IPE_TONE_RECEIPT '),bootstrap=text.count('IPE_TONE_BOOTSTRAP '))
  assert code==0 and 'ADAPT_RESULT ' in text and 'failed=0 result=0' in text and 'FIXTURE_RESTORATION result=0' in text,text[-3500:]
  assert 'pd10=1 result=0' in text and 'IPE_TONE_REJECT' not in text and 'IFE_GTM_REJECT' not in text
  assert state['captures'][name]['tone_prepares']>0 and state['captures'][name]['gtm_applied']>1
  idle();s=status();assert s['completed']-before>=state['captures'][name]['frames'] and not any(s[k] for k in ['failed','cancelled','first_error','fatal'])
  state['captures'][name]['ipe_completed']=s['completed']-before
 state['candidate_final_status']=status();state['candidate_final_core']=core();verified=True
