 state['captures']={}
 for model,size in [('imx319','1632x1224'),('s5k3m5','2104x1560')]:
  nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith(model+' ')];assert len(nodes)==1
  name=model+'-scene-native';case=root/name;case.mkdir()
  env=dict(os.environ,LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG',CAPTURE_DIR=str(case))
  for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION','LIBCAMERA_CAMSS_VFE_TRACE_DIR']:env.pop(n,None)
  env.update(LD_LIBRARY_PATH=str(root/'lib'),LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(root/'proxy'),LIBCAMERA_CAMSS_VFE_PROFILE=str(root/('factory-'+model+'-private.yaml')))
  before=status()['completed']
  with (case/'client.log').open('xb') as log:
   child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'capture'),model,'/dev/'+nodes[0].name,size,'0'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save('automatic-tone-'+model,client_pid=child.pid);code=child.wait(timeout=35)
  text=(case/'client.log').read_text(errors='replace')
  result=re.findall(r'AWB_STEADY_RESULT locked-frames=(\d+) final-locked-run=(\d+)',text);assert len(result)==1,text[-3500:]
  state['captures'][name]=dict(model=model,sensor_size=size,exit_code=code,frames=text.count('ADAPT_FRAME '),pd10_ready=text.count('PD10_READY '),gtm_applied=text.count('IFE_GTM_APPLIED '),tone_prepares=text.count('IPE_TONE_PREPARE '),tone_receipts=text.count('IPE_TONE_RECEIPT '),bootstrap=text.count('IPE_TONE_BOOTSTRAP '),locked_frames=int(result[0][0]),final_locked_run=int(result[0][1]))
  assert code==0 and 'failed=0 result=0' in text and 'FIXTURE_RESTORATION result=0' in text,text[-3500:]
  assert 'pd10=1 result=0' in text and 'IPE_TONE_REJECT' not in text and 'IFE_GTM_REJECT' not in text
  assert state['captures'][name]['tone_receipts']>0 and state['captures'][name]['gtm_applied']>1
  idle();s=status();assert s['completed']-before==state['captures'][name]['frames'] and not any(s[k] for k in ['failed','cancelled','first_error','fatal'])
  state['captures'][name]['ipe_completed']=s['completed']-before
 state['candidate_final_status']=status();state['candidate_final_core']=core();verified=True
