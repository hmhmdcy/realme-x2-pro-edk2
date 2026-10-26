 state['captures']={}
 nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith('imx471 ')];assert len(nodes)==1
 for isolated in [False,True]:
  name='scene-isolated' if isolated else 'scene-native';case=root/name;case.mkdir()
  env=dict(os.environ,LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG',CAPTURE_DIR=str(case))
  for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION','LIBCAMERA_CAMSS_VFE_TRACE_DIR']:env.pop(n,None)
  env.update(LD_LIBRARY_PATH=str(root/'lib'),LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(root/'proxy'),LIBCAMERA_CAMSS_VFE_PROFILE=str(root/'factory-imx471-private.yaml'),LIBCAMERA_CAMSS_VFE_TRACE_DIR=str(case))
  if isolated:env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'
  before=status()['completed']
  with (case/'client.log').open('xb') as log:
   child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'capture'),'imx471','/dev/'+nodes[0].name,'2304x1728','0'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save('front-automatic-ipe-colour-'+name,client_pid=child.pid);code=child.wait(timeout=40)
  text=(case/'client.log').read_text(errors='replace')
  result=re.findall(r'AWB_STEADY_RESULT locked-frames=(\d+) final-locked-run=(\d+)',text);assert len(result)==1,text[-3500:]
  traces=re.findall(r'IPE_TONE_TRACE epoch=(\d+) sof=(\d+) token=(\d+) revision=(\d+) full-sequence=(\d+) pd10-sequence=(\d+) result=(-?\d+)',text)
  state['captures'][name]=dict(model='imx471',sensor_size='2304x1728',exit_code=code,frames=text.count('ADAPT_FRAME '),pd10_ready=text.count('PD10_READY '),gtm_applied=text.count('IFE_GTM_APPLIED '),tone_prepares=text.count('IPE_TONE_PREPARE '),ccm_prepares=text.count('IPE_CCM_PREPARE '),tone_receipts=text.count('IPE_TONE_RECEIPT '),bootstrap=text.count('IPE_TONE_BOOTSTRAP '),locked_frames=int(result[0][0]),final_locked_run=int(result[0][1]))
  assert code==0 and 'failed=0 result=0' in text and 'FIXTURE_RESTORATION result=0' in text,text[-3500:]
  assert 'pd10=1 result=0' in text and 'IPE_TONE_REJECT' not in text and 'IFE_GTM_REJECT' not in text
  assert state['captures'][name]['final_locked_run']>=8
  assert state['captures'][name]['ccm_prepares']==state['captures'][name]['tone_prepares']>0
  frames=[line for line in text.splitlines() if line.startswith('ADAPT_FRAME ')]
  assert all(' matrix=' in line for line in frames)
  assert len(traces)==1 and traces[0][-1]=='0'
  epoch,sof,token,revision,full,coarse,result=map(int,traces[0]);assert full==coarse and sof>=12 and revision>0
  for suffix,size in [('-full.nv12',460800),('-coarse.pd10',46080),('-params.bin',6008)]:assert (case/('tone-'+str(sof)+suffix)).stat().st_size==size
  assert (case/('frame-'+str(sof)+'.nv12')).stat().st_size==460800
  state['captures'][name]['trace']=dict(epoch=epoch,sof=sof,token=token,revision=revision,full_kernel_sequence=full,pd10_kernel_sequence=coarse,same_frame_output_saved=True)
  idle();s=status();assert s['completed']-before==len(frames) and not any(s[k] for k in ['failed','cancelled','first_error','fatal'])
  state['captures'][name]['ipe_completed']=s['completed']-before
 # Replay the exact native FULL/PD10/IPA packet without modifying source pixels.
 import fcntl
 video=[str(Path('/dev')/p.parent.name) for p in Path('/sys/class/video4linux').glob('video*/name') if p.read_text().strip()=='qcom-ipe-a5'];assert len(video)==1
 media=[]
 for path in Path('/dev').glob('media[0-9]*'):
  try:
   with path.open('rb',buffering=0) as f:data=bytearray(256);fcntl.ioctl(f.fileno(),0xc1007c00,data,True)
   if bytes(data[16:48]).split(b'\0')[0].decode()=='SM8150 IPE':media.append(str(path))
  except OSError:continue
 assert len(media)==1
 case=root/'replay';case.mkdir();sof=state['captures']['scene-native']['trace']['sof'];native=root/'scene-native'
 for old,new in [(f'tone-{sof}-full.nv12','full-private.bin'),(f'tone-{sof}-coarse.pd10','pd10-private.bin'),(f'tone-{sof}-params.bin','parameters-private.bin')]:shutil.copyfile(native/old,case/new)
 before=status()['completed']
 with (case/'client.log').open('xb') as log:
  child=subprocess.Popen([str(root/'tone-replay'),video[0],media[0],str(case)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  save('front-fixed-input-ltm-ccm-replay',client_pid=child.pid);code=child.wait(timeout=45)
 text=(case/'client.log').read_text(errors='replace');assert code==0 and 'TONE_REPLAY_RESULT result=0 frames=5' in text,text[-3000:]
 rows=re.findall(r'REPLAY_FRAME mode=(\d+) flags=(\d+) full=([0-9a-f]+) pd10=([0-9a-f]+) output=([0-9a-f]+)',text)
 assert len(rows)==5 and len({r[2] for r in rows})==len({r[3] for r in rows})==1
 raw=[(case/f'mode-{i}-output-private.bin').read_bytes() for i in range(5)]
 assert raw[0]==raw[4]==(native/f'frame-{sof}.nv12').read_bytes()
 assert raw[0]!=raw[1] and raw[0]!=raw[2]
 state['replay']=dict(frames=5,source_sof=sof,stock_repeat_equal=True,stock_matches_live=True,ltm_changes_pixels=True,ipe_ccm_changes_pixels=True)
 idle();s=status();assert s['completed']-before==5 and not any(s[k] for k in ['failed','cancelled','first_error','fatal'])
 state['candidate_final_status']=status();state['candidate_final_core']=core();verified=True
