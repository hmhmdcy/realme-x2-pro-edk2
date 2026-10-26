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
