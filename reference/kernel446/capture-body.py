 state['focus_benchmarks']={}
 fixtures=json.loads((root/'focus-fixtures-private.json').read_text());assert len(fixtures)==4
 for fixture in fixtures:
  path=Path(fixture['phone_path']);assert str(path).startswith('/var/lib/samurai/k442-callback-timing-r9/')
  assert hashlib.sha256(path.read_bytes()).hexdigest()==fixture['sha256']
  label=fixture['label'];logpath=root/('focus-bench-'+label+'.log')
  with logpath.open('xb') as output:
   child=subprocess.Popen([str(root/'focus-bench'),str(path),str(fixture['width']),str(fixture['height']),str(fixture['stride']),'16',str(fixture['score'])],stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
   save('focus-benchmark-'+label,client_pid=child.pid);code=child.wait(timeout=35)
  result=json.loads(logpath.read_text());assert code==0 and result['fixture_passed'] and result['checksum_consistent']
  state['focus_benchmarks'][label]=dict(**result,alternating_old_new_order=True,cached_full_not_dma=True)
 state['captures']={}
 devices=[p for p in Path('/sys/bus/i2c/drivers/s5kgw1').iterdir() if (p/'of_node').exists()];assert len(devices)==1
 camera_id='/base'+str((devices[0]/'of_node').resolve()).split('/base',1)[1]
 nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith('s5kgw1 ')];assert len(nodes)==1
 for width,height,coarse_bytes in [(1280,720,123648),(1920,1080,261120)]:
  for isolated in [True]:
   name=f'{width}x{height}-'+('isolated' if isolated else 'native');case=root/name;case.mkdir()
   env=dict(os.environ,LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
   for n in list(env):
    if n=='LD_LIBRARY_PATH' or n.startswith(('LIBCAMERA_','CAPTURE_','GST_')):env.pop(n,None)
   env.update(LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG',LD_LIBRARY_PATH=str(root/'lib'),LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(root/'proxy'),LIBCAMERA_CAMSS_VFE_PROFILE=str(root/'factory-s5kgw1-private.yaml'),GST_TARGET_FRAMES='120',GST_SENSOR_NODE='/dev/'+nodes[0].name)
   if isolated:env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'
   before=status()['completed'];launched=time.monotonic()
   with (case/'client.log').open('xb') as log:
    child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'gst-hardware-probe'),camera_id,str(width),str(height)],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    save('capture-'+name,client_pid=child.pid)
    deadline=time.monotonic()+10
    while True:
     text=(case/'client.log').read_text(errors='replace');pids=re.findall(r'APPLICATION_PROCESS pid=(\d+)',text)
     if len(pids)==1 and 'GST_IMAGE ' in text:
      actual_pid=int(pids[0]);maps=Path('/proc',str(actual_pid),'maps').read_text()
      assert str(root/'lib/libcamera.so.0.7.2') in maps
      plugins={line.split()[-1] for line in maps.splitlines() if line.split()[-1].endswith('/libgstlibcamera.so')};assert len(plugins)==1
      plugin=Path(next(iter(plugins)));plugin_sha=hashlib.sha256(plugin.read_bytes()).hexdigest();break
     assert child.poll() is None and time.monotonic()<deadline,text[-2500:]
     time.sleep(.02)
    code=child.wait(timeout=65)
   text=(case/'client.log').read_text(errors='replace')
   summary=dict(model='s5kgw1',width=width,height=height,coarse_bytes=coarse_bytes,isolated=isolated,exit_code=code,frames=text.count('GST_IMAGE '),elapsed_seconds=round(time.monotonic()-launched,3),mapped_candidate_core=True,plugin_sha256=plugin_sha)
   state['captures'][name]=summary
   assert code==0 and f'GST_RESULT frames=120 width={width} height={height} bus-errors=0 result=0' in text and 'FIXTURE_RESTORATION result=0' in text,text[-3000:]
   sensor=re.findall(r'GST_SENSOR width=(\d+) height=(\d+) code=(\d+)',text);assert len(sensor)==1 and tuple(map(int,sensor[0][:2]))==(4608,2592)
   summary['actual_sensor']=[4608,2592]
   ipa_pids={int(p) for p in re.findall(r'IPA stats pid=(\d+)',text)};assert len(ipa_pids)==1 and (actual_pid in ipa_pids)==(not isolated)
   focused=re.findall(r'FRAME_IPA_PREPARE epoch=1 sof=(\d+) combined=(\d+) focus-us=(\d+) dispatch-us=(\d+) focus-status=(-?\d+) tone-prepared=(\d+)',text)
   assert len(focused)>=summary['frames'] and all(r[1]=='1' and r[4]=='0' and r[5]=='1' for r in focused)
   summary['combined_focus_tone_calls']=len(focused)
   idle();s=status();summary['ipe_completed']=s['completed']-before
   assert summary['frames']<=summary['ipe_completed'] and not any(s[k] for k in ['failed','cancelled','first_error','fatal'])
   assert 'PD10_READY ' in text and 'IPE_TONE_QUEUE ' in text and 'REQUEST_STOP_CANCEL ' in text
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
 state['compatibility']={}
 for kind in ['raw','dual']:
  name='compatibility-'+kind;case=root/name;case.mkdir()
  env=dict(os.environ,LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
  for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_CAMSS_VFE_TRACE_DIR','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(n,None)
  env.update(LD_LIBRARY_PATH=str(root/'lib'),LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(root/'proxy'),LIBCAMERA_CAMSS_VFE_PROFILE=str(root/'factory-s5kgw1-private.yaml'),LIBCAMERA_IPA_FORCE_ISOLATION='1',RAW_TARGET_FRAMES='6')
  before=status()['completed']
  with (case/'client.log').open('xb') as log:
   child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'pipeline-smoke'),'s5kgw1@4608x3456',kind],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save('compatibility-'+kind,client_pid=child.pid);code=child.wait(timeout=40)
  text=(case/'client.log').read_text(errors='replace')
  assert code==0 and 'failed=0 result=0' in text and 'FIXTURE_RESTORATION result=0' in text,text[-3000:]
  result=re.findall(r'RAW_RESULT .* frames=(\d+) .* failed=0 result=0',text);assert len(result)==1
  frames=int(result[0]);assert frames==6
  pairs=re.findall(r'RawPair .* matched=(\d+)',text);assert len(pairs)==frames and all(v=='1' for v in pairs)
  idle();delta=status()['completed']-before
  assert delta==0 if kind=='raw' else frames<=delta<=frames+1
  if kind=='raw':assert 'PD10_READY ' not in text and 'IPE_TONE_QUEUE ' not in text
  assert text.count('REQUEST_STOP_CANCEL ')>0
  state['compatibility'][kind]=dict(frames=frames,ipe_completed=delta,raw_pair_same_sof=True,stop_cancel_requests=text.count('REQUEST_STOP_CANCEL '),passed=True)
 state['candidate_final_status']=status();state['candidate_final_core']=core();verified=True
