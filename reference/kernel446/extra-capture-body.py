 state['other_captures']={}
 cases=[('imx319','1632x1224',False),('s5k3m5','2104x1560',False),('imx471','2304x1728',False),('s5kgw1','4608x3456',True)]
 for model,sensor_size,af in cases:
  name=model+('-af' if af else '-scene')+'-isolated';case=root/name;case.mkdir()
  nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith(model+' ')];assert len(nodes)==1
  env=dict(os.environ)
  for n in list(env):
   if n=='LD_LIBRARY_PATH' or n.startswith(('LIBCAMERA_','CAPTURE_','GST_')):env.pop(n,None)
  env.update(LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG',CAPTURE_DIR=str(case),LD_LIBRARY_PATH=str(root/'lib'),LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(root/'proxy'),LIBCAMERA_CAMSS_VFE_PROFILE=str(root/('factory-'+model+'-private.yaml')),LIBCAMERA_IPA_FORCE_ISOLATION='1')
  before=status()['completed'];launched=time.monotonic()
  with (case/'client.log').open('xb') as log:
   child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/('af-capture' if af else 'capture')),model,'/dev/'+nodes[0].name,sensor_size,'0'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save('capture-'+name,client_pid=child.pid);code=child.wait(timeout=140 if af else 40)
  text=(case/'client.log').read_text(errors='replace')
  summary=dict(model=model,width=640,height=480,coarse_bytes=46080,sensor_size=sensor_size,isolated=True,af=af,exit_code=code,frames=text.count('ADAPT_FRAME '),elapsed_seconds=round(time.monotonic()-launched,3))
  state['other_captures'][name]=summary
  assert code==0 and 'failed=0 result=0' in text and 'FIXTURE_RESTORATION result=0' in text,text[-3500:]
  locked=re.findall(r'AWB_STEADY_RESULT locked-frames=(\d+) final-locked-run=(\d+)',text);assert len(locked)==1 and int(locked[0][1])>=8
  app={int(p) for p in re.findall(r'ADAPT_PID value=(\d+)',text)};ipa={int(p) for p in re.findall(r'IPA stats pid=(\d+)',text)}
  assert len(app)==len(ipa)==1 and not app&ipa
  assert 'pd10=1 result=0' in text and not any(x in text for x in ['IPE_TONE_REJECT','IFE_GTM_REJECT','IMAGE_PAIR_TIMEOUT'])
  if af:
   result=re.findall(r'AF_TRIGGER_RESULT scanning=(\d+) terminal=(-?\d+) focused=(\d+)',text);assert len(result)==1 and result[0][0]=='1' and int(result[0][1]) in [2,3]
   summary.update(af_scanned=True,af_terminal=int(result[0][1]),af_focused=result[0][2]=='1')
  idle();s=status();summary['ipe_completed']=s['completed']-before
  assert summary['frames']<=summary['ipe_completed']<=summary['frames']+1
  assert not any(s[k] for k in ['failed','cancelled','first_error','fatal'])
