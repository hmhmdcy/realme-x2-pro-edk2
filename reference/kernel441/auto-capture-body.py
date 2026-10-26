 import resource
 def capture_core_limit():resource.setrlimit(resource.RLIMIT_CORE,(256*1024*1024,256*1024*1024))
 diagnostic=(root/'diagnostic.json').exists()
 state['captures']={};state['replays']={}
 nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith('s5kgw1 ')]
 assert len(nodes)==1
 for width,height,coarse_bytes,scratch_bytes in [(1280,720,123648,121008),(1920,1080,261120,261168)]:
  size=f'{width}x{height}'
  if diagnostic and width!=1920:continue
  for isolated in [False,True]:
   if diagnostic and not isolated:continue
   name=size+('-isolated' if isolated else '-native');case=root/name;case.mkdir()
   env=dict(os.environ,LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG',CAPTURE_DIR=str(case))
   for n in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_IPA_FORCE_ISOLATION','LIBCAMERA_CAMSS_VFE_TRACE_DIR']:env.pop(n,None)
   env.update(LD_LIBRARY_PATH=str(root/'lib'),LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(root/'proxy'),LIBCAMERA_CAMSS_VFE_PROFILE=str(root/'factory-s5kgw1-private.yaml'),LIBCAMERA_CAMSS_VFE_TRACE_DIR=str(case))
   if isolated:env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'
   before=status()['completed']
   with (case/'client.log').open('xb') as log:
    child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'capture'),'s5kgw1','/dev/'+nodes[0].name,'4608x3456','0',size],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=capture_core_limit,cwd=str(case))
    save('capture-'+name,client_pid=child.pid);code=child.wait(timeout=40)
   text=(case/'client.log').read_text(errors='replace')
   summary=dict(model='s5kgw1',width=width,height=height,coarse_bytes=coarse_bytes,isolated=isolated,exit_code=code,frames=text.count('ADAPT_FRAME '))
   state['captures'][name]=summary
   assert code==0 and 'failed=0 result=0' in text and 'FIXTURE_RESTORATION result=0' in text,text[-3500:]
   locked=re.findall(r'AWB_STEADY_RESULT locked-frames=(\d+) final-locked-run=(\d+)',text)
   assert len(locked)==1 and int(locked[0][1])>=8
   traces=re.findall(r'IPE_TONE_TRACE epoch=(\d+) sof=(\d+) token=(\d+) revision=(\d+) full-sequence=(\d+) pd10-sequence=(\d+) result=(-?\d+)',text)
   assert len(traces)==1 and traces[0][-1]=='0'
   epoch,sof,token,revision,full,coarse,result=map(int,traces[0]);assert full==coarse and revision>0
   for suffix,length in [('-full.nv12',width*height*3//2),('-coarse.pd10',coarse_bytes),('-params.bin',6008)]:assert (case/f'tone-{sof}{suffix}').stat().st_size==length
   summary['trace']=dict(sof=sof,token=token,revision=revision,full_kernel_sequence=full,pd10_kernel_sequence=coarse)
   idle();s=status();summary['ipe_completed']=s['completed']-before
   # Shutdown may complete one queued image whose application callback was cancelled.
   assert summary['frames']<=summary['ipe_completed']<=summary['frames']+1
   assert not any(s[k] for k in ['failed','cancelled','first_error','fatal'])
  if diagnostic:continue
  import fcntl
  video=[str(Path('/dev')/p.parent.name) for p in Path('/sys/class/video4linux').glob('video*/name') if p.read_text().strip()=='qcom-ipe-a5']
  media=[]
  for path in Path('/dev').glob('media[0-9]*'):
   try:
    with path.open('rb',buffering=0) as f:
     data=bytearray(256);fcntl.ioctl(f.fileno(),0xc1007c00,data,True)
    if bytes(data[16:48]).split(b'\0')[0]==b'SM8150 IPE':media.append(str(path))
   except OSError:continue
  assert len(video)==len(media)==1
  source=root/(size+'-native');sof=state['captures'][source.name]['trace']['sof']
  case=root/(size+'-replay');case.mkdir()
  for target,suffix in [('full-private.bin','-full.nv12'),('pd10-private.bin','-coarse.pd10'),('parameters-private.bin','-params.bin')]:shutil.copyfile(source/f'tone-{sof}{suffix}',case/target)
  before=status()['completed']
  with (case/'client.log').open('xb') as log:
   child=subprocess.Popen([str(root/'pd10-ipe'),video[0],media[0],str(case),str(width),str(height),str(scratch_bytes)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   save('replay-'+size,client_pid=child.pid);code=child.wait(timeout=55)
  text=(case/'client.log').read_text(errors='replace');state['replays'][size]=dict(width=width,height=height,source_sof=sof,exit_code=code)
  assert code==0 and 'PD10_IPE_RESULT result=0 frames=4' in text,text[-3000:]
  outputs=[(case/f'mode-{i}-output-private.bin').read_bytes() for i in range(4)]
  assert all(len(x)==width*height*3//2 for x in outputs)
  assert outputs[0]==outputs[3] and outputs[0]!=outputs[1] and outputs[0]!=outputs[2] and outputs[1]!=outputs[2]
  idle();s=status();assert s['completed']-before==4 and not any(s[k] for k in ['failed','cancelled','first_error','fatal'])
  state['replays'][size].update(real_input_repeat_equal=True,only_pd10_changes_full_output=True,ipe_completed=4,passed=True)
 state['candidate_final_status']=status();state['candidate_final_core']=core();verified=True
