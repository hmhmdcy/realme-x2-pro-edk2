"""Default installed lookup paths: four GStreamer cameras, RAW and automatic IQ."""
dev=Path('/sys/bus/platform/devices/ac10000.icp');captures={};failure=None
def status():
 s=json.loads((dev/'m2m_status').read_text());c=json.loads((dev/'state').read_text())
 assert s['direct_completed']==s['completed'] and s['jobs']==s['completed']+s['cancelled']
 assert not any(s[k] for k in ['users','running','pinned','orphans','fatal','failed','first_error'])
 assert not c['copy_frames'] and c['direct_frames']==c['frames_completed'] and not c['imported_buffers'] and not c['imported_bytes']
 return s
def capture(args,label,env,expect_ipe=True):
 with (root/(label+'.log')).open('xb') as output:
  child=subprocess.Popen(args,env=env,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
  save(label,child_pid=child.pid)
  try:code=child.wait(timeout=45)
  except subprocess.TimeoutExpired:
   os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
   raise
 text=(root/(label+'.log')).read_text(errors='replace')
 assert code==0 and 'FIXTURE_RESTORATION result=0' in text,(label,code,text[-3000:])
 assert ('IPE enabled ' in text)==expect_ipe,label
 wait_idle();return text
try:
 proof=json.loads((root/'proof.json').read_text())
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==proof['boot_id'] and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 assert not any(processes(n) for n in ['pipewire','wireplumber']);wait_idle()
 if 'reuse_cases' in proof:
  reuse=proof['reuse_cases'];prior=Path(reuse['root'])
  assert hashlib.sha256((prior/'proof.json').read_bytes()).hexdigest()==reuse['proof_sha256']
  assert hashlib.sha256((prior/'suite.json').read_bytes()).hexdigest()==reuse['suite_sha256']
  for name,row in reuse['captures'].items():
   assert hashlib.sha256((prior/(name+'.log')).read_bytes()).hexdigest()==reuse['log_sha256'][name]
   assert row['passed'];captures[name]=dict(**row,reused_from=str(prior))
 env=dict(os.environ,LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
 for key in list(env):
  if key=='LD_LIBRARY_PATH' or key.startswith('LIBCAMERA_') and key!='LIBCAMERA_LOG_LEVELS' or key in ['CAPTURE_DIR','RAW_TARGET_FRAMES']:env.pop(key,None)
 assert not any(k in env for k in ['LD_LIBRARY_PATH','LIBCAMERA_CAMSS_VFE_PROFILE','LIBCAMERA_IPA_MODULE_PATH','LIBCAMERA_IPA_PROXY_PATH'])
 previous=status()
 for model in ['imx471','imx319','s5k3m5','s5kgw1']:
  if 'gst-'+model in captures:continue
  devices=[p for p in Path('/sys/bus/i2c/drivers',model).iterdir() if (p/'of_node').exists()];assert len(devices)==1
  camera_id='/base'+str((devices[0]/'of_node').resolve()).split('/base',1)[1]
  text=capture([str(root/'pipeline-fixture'),'/dev/media0',str(root/'gst-hardware-probe'),camera_id,'640','480'],'gst-'+model,env)
  match=re.search(r'GST_RESULT frames=(\d+) width=(\d+) height=(\d+) bus-errors=(\d+) result=(\d+)',text)
  assert match and int(match[1])>0 and (int(match[2]),int(match[3]))==(640,480) and not int(match[4]) and not int(match[5])
  current=status();delta=current['completed']-previous['completed'];assert delta>=int(match[1])
  captures['gst-'+model]=dict(frames=int(match[1]),ipe_completed=delta,ipe_cancelled=current['cancelled']-previous['cancelled'],passed=True);previous=current
 for kind in ['dual','raw']:
  if 'raw-'+kind in captures:continue
  text=capture([str(root/'pipeline-fixture'),'/dev/media0',str(root/'pipeline-smoke'),'s5kgw1@4608x3456',kind],'raw-'+kind,env,kind=='dual')
  assert 'failed=0 result=0' in text
  pairs=re.findall(r'RawPair .* matched=(\d+)',text);assert len(pairs)==6 and all(x=='1' for x in pairs)
  current=status();delta=current['completed']-previous['completed'];cancelled=current['cancelled']-previous['cancelled']
  histories=re.findall(r'IPE_HISTORY_STOP epoch=\d+ prepared=(\d+) committed=(\d+) discarded=(\d+) superseded=(\d+) aborted=(\d+) pending=(\d+)',text);assert len(histories)==1
  prepared,committed,discarded,superseded,aborted,pending=map(int,histories[0]);assert not superseded and not pending and prepared==committed+discarded+aborted
  queues=re.findall(r'IPE_TONE_QUEUE .* result=0',text)
  receipts=re.findall(r'IPE_RECEIPT .* success=(\d+) result=(\d+)',text)
  if kind=='dual':
   # A sixth callback may race one already queued IPE job at stop. Physical
   # completion still counts; a stopped request must never advance IPA history.
   successes=sum(s=='1' and r=='1' for s,r in receipts);aborts=sum(s=='0' and r=='0' for s,r in receipts)
   assert successes==committed==6 and len(queues) in [6,7] and delta+cancelled==len(queues)
   assert len(receipts)==len(queues) and aborts==aborted==len(queues)-6
   assert delta>=6 and cancelled<=aborted
  else:
   assert delta==cancelled==committed==aborted==0 and discarded==prepared and prepared>=6
   assert not any(x in text for x in ['PD10_READY ','IPE_TONE_PREPARE ','IPE_TONE_QUEUE '])
  captures['raw-'+kind]=dict(frames=6,raw_pairs=len(pairs),ipe_completed=delta,ipe_cancelled=cancelled,successful_observations=committed,stop_aborted_queued_images=aborted,stop_discarded_unqueued_observations=discarded,passed=True);previous=current
 # The complete preinstallation eight-path suite already proves all four IQ chains.
 # These two captures verify that default installed lookup selects each CCM domain.
 for model,size in [('s5kgw1','4608x3456'),('imx471','2304x1728')]:
  if 'auto-'+model in captures:continue
  nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith(model+' ')];assert len(nodes)==1
  folder=root/('auto-'+model);folder.mkdir();capture_env=dict(env,CAPTURE_DIR=str(folder))
  text=capture([str(root/'pipeline-fixture'),'/dev/media0',str(root/'capture'),model,'/dev/'+nodes[0].name,size,'0'],'auto-'+model,capture_env)
  audited=audit_auto(text,model,folder);frames=audited['frames']
  assert 'ADAPT_LIBRARY path=/usr/lib/libcamera.so.0.7.2' in text
  assert len(list(folder.glob('frame-*.nv12')))==frames
  current=status();delta=current['completed']-previous['completed'];cancelled=current['cancelled']-previous['cancelled'];assert delta+cancelled==audited['queued_images'] and delta>=frames
  captures['auto-'+model]=dict(**audited,ipe_completed=delta,ipe_cancelled=cancelled);previous=current
except BaseException:
 failure=traceback.format_exc();(root/'camera-failure.txt').write_text(failure)
finally:
 try:wait_idle();final=status();restored=not any(processes(n) for n in ['pipewire','wireplumber'])
 except BaseException:restored=False;final=None;(root/'camera-cleanup-failure.txt').write_text(traceback.format_exc())
 report=dict(stage=440,captures=captures,default_paths_without_ld_or_profile_or_ipa_overrides=True,services_kept_stopped_for_outer=restored,failure=failure,taint=int(Path('/proc/sys/kernel/tainted').read_text()),m2m_final=final)
 report['passed']=bool(not failure and restored and len(captures)==8 and report['taint']==0)
 save('finished',terminal=True,passed=report['passed']);print(json.dumps(report),flush=True)
sys.exit(0 if report['passed'] else 1)
