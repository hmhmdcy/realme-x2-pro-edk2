 state['captures']={}
 for model,size in [('s5kgw1','4608x3456'),('imx319','1632x1224'),('s5k3m5','2104x1560'),('imx471','2304x1728')]:
  nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith(model+' ')];assert len(nodes)==1
  for isolated in [False,True]:
   name=model+('-scene-isolated' if isolated else '-scene-native');case=root/name;case.mkdir()
   env=dict(os.environ,LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG',CAPTURE_DIR=str(case))
   for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION','LIBCAMERA_CAMSS_VFE_TRACE_DIR']:env.pop(n,None)
   env.update(LD_LIBRARY_PATH=str(root/'lib'),LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(root/'proxy'),LIBCAMERA_CAMSS_VFE_PROFILE=str(root/f'factory-{model}-private.yaml'),LIBCAMERA_CAMSS_VFE_TRACE_DIR=str(case))
   if isolated:env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'
   before=status()['completed']
   with (case/'client.log').open('xb') as log:
    child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'capture'),model,'/dev/'+nodes[0].name,size,'0'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    save('packaged-four-camera-'+name,client_pid=child.pid);code=child.wait(timeout=40)
   text=(case/'client.log').read_text(errors='replace');result=re.findall(r'AWB_STEADY_RESULT locked-frames=(\d+) final-locked-run=(\d+)',text);assert len(result)==1,text[-3500:]
   traces=re.findall(r'IPE_TONE_TRACE epoch=(\d+) sof=(\d+) token=(\d+) revision=(\d+) full-sequence=(\d+) pd10-sequence=(\d+) result=(-?\d+)',text)
   summary=dict(model=model,sensor_size=size,isolated=isolated,exit_code=code,frames=text.count('ADAPT_FRAME '),pd10_ready=text.count('PD10_READY '),gtm_applied=text.count('IFE_GTM_APPLIED '),tone_prepares=text.count('IPE_TONE_PREPARE '),ccm_prepares=text.count('IPE_CCM_PREPARE '),tone_receipts=text.count('IPE_TONE_RECEIPT '),bootstrap=text.count('IPE_TONE_BOOTSTRAP '),locked_frames=int(result[0][0]),final_locked_run=int(result[0][1]));state['captures'][name]=summary
   assert code==0 and 'failed=0 result=0' in text and 'FIXTURE_RESTORATION result=0' in text,text[-3500:]
   assert 'pd10=1 result=0' in text and 'IPE_TONE_REJECT' not in text and 'IFE_GTM_REJECT' not in text and summary['final_locked_run']>=8
   assert (summary['ccm_prepares']==summary['tone_prepares']>0) if model=='imx471' else summary['ccm_prepares']==0
   frames=[line for line in text.splitlines() if line.startswith('ADAPT_FRAME ')];assert all(' matrix=' in line for line in frames)
   assert len(traces)==1 and traces[0][-1]=='0';epoch,sof,token,revision,full,coarse,result=map(int,traces[0]);assert full==coarse and sof>=12 and revision>0
   for suffix,length in [('-full.nv12',460800),('-coarse.pd10',46080),('-params.bin',6008)]:assert (case/f'tone-{sof}{suffix}').stat().st_size==length
   summary['trace']=dict(epoch=epoch,sof=sof,token=token,revision=revision,full_kernel_sequence=full,pd10_kernel_sequence=coarse,same_frame_output_saved=True)
   idle();s=status();assert s['completed']-before==len(frames) and not any(s[k] for k in ['failed','cancelled','first_error','fatal']);summary['ipe_completed']=s['completed']-before
 state['raw']={}
 for model,size,kind in [('s5kgw1','4608x3456','dual'),('s5kgw1','4608x3456','raw'),('imx319','1632x1224','raw'),('s5k3m5','2104x1560','raw'),('imx471','2304x1728','raw')]:
  name=model+'-raw-'+kind;case=root/name;case.mkdir();env=dict(os.environ,LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
  for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_IPA_FORCE_ISOLATION','LIBCAMERA_CAMSS_VFE_TRACE_DIR']:env.pop(n,None)
  env.update(LD_LIBRARY_PATH=str(root/'lib'),LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(root/'proxy'),LIBCAMERA_CAMSS_VFE_PROFILE=str(root/f'factory-{model}-private.yaml'))
  env.pop('RAW_TARGET_FRAMES',None)
  if kind=='raw' and model=='s5kgw1':env['RAW_TARGET_FRAMES']='72'
  before=status()['completed']
  with (case/'client.log').open('xb') as log:
   child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'pipeline-smoke'),model+'@'+size,kind],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save('packaged-'+name,client_pid=child.pid);code=child.wait(timeout=40)
  text=(case/'client.log').read_text(errors='replace');assert code==0 and 'failed=0 result=0' in text and 'FIXTURE_RESTORATION result=0' in text,text[-3000:]
  pairs=re.findall(r'RawPair .* matched=(\d+)',text);assert pairs and all(x=='1' for x in pairs)
  idle();delta=status()['completed']-before;assert delta>0 if kind=='dual' else delta==0
  result=re.findall(r'RAW_RESULT .* frames=(\d+) .* failed=0 result=0',text);assert len(result)==1
  if kind=='raw':assert 'PD10_READY ' not in text and 'IPE_TONE_PREPARE ' not in text and 'IPE_TONE_QUEUE ' not in text
  state['raw'][name]=dict(model=model,kind=kind,frames=int(result[0]),ipe_completed=delta,raw_pairs=len(pairs),passed=True)
 state['candidate_final_status']=status();state['candidate_final_core']=core();verified=True
