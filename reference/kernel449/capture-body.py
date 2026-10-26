 state['captures']={};state['sustained']={}
 import pwd
 uid=10000;account=pwd.getpwuid(uid)
 nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith('s5kgw1 ')];assert len(nodes)==1
 devices=[p for p in Path('/sys/bus/i2c/drivers/s5kgw1').iterdir() if (p/'of_node').exists()];assert len(devices)==1
 camera_id='/base'+str((devices[0]/'of_node').resolve()).split('/base',1)[1]
 for name,isolated,sustained in [('user-native',False,False),('user-isolated',True,False),('user-sustained-1080',True,True)]:
  case=root/name;case.mkdir();userroot=Path('/run/user/10000')/('k449-user-'+root.name.rsplit('-',1)[1]+'-'+name)
  assert not userroot.exists();userroot.mkdir(mode=0o700);observer=None;observer_log=None
  try:
   for n in ['lib','ipa','proxy','captures']:(userroot/n).mkdir(mode=0o700)
   relative=list(json.loads((root/'manifest.json').read_text()))
   chosen=[n for n in relative if n.startswith(('lib/','ipa/','proxy/'))]+['factory-s5kgw1-private.yaml','lifecycle','gst-sustained']
   for n in chosen:
    target=userroot/n;shutil.copyfile(root/n,target);target.chmod(0o700 if n in ['lifecycle','gst-sustained','proxy/camss_ipa_proxy'] else 0o600)
    assert hashlib.sha256(target.read_bytes()).hexdigest()==hashlib.sha256((root/n).read_bytes()).hexdigest()
   for n in ['libcamera','libcamera-base']:(userroot/f'lib/{n}.so.0.7').symlink_to(f'{n}.so.0.7.2')
   for p in [userroot,*userroot.rglob('*')]:
    if p.is_symlink():os.lchown(p,uid,account.pw_gid)
    else:os.chown(p,uid,account.pw_gid)
   env=dict(os.environ)
   for n in list(env):
    if n=='LD_LIBRARY_PATH' or n.startswith(('LIBCAMERA_','CAPTURE_','GST_')):env.pop(n,None)
   env.update(LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG',LD_LIBRARY_PATH=str(userroot/'lib'),LIBCAMERA_IPA_MODULE_PATH=str(userroot/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(userroot/'proxy'),LIBCAMERA_CAMSS_VFE_PROFILE=str(userroot/'factory-s5kgw1-private.yaml'),CAPTURE_DIR=str(userroot/'captures'),GST_TARGET_FRAMES='9000',GST_SENSOR_NODE='/dev/'+nodes[0].name)
   if isolated:env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'
   arguments=['gst-sustained',camera_id,'1920','1080'] if sustained else ['lifecycle','s5kgw1','/dev/'+nodes[0].name,'4608x2592','0']
   before=status()['completed'];launched=time.monotonic()
   if sustained:
    observer_log=(case/'conditions.log').open('xb');observer=subprocess.Popen(['python3',str(root/'conditions-observer.py')],stdin=subprocess.DEVNULL,stdout=observer_log,stderr=subprocess.STDOUT,start_new_session=True)
   with (case/'client.log').open('xb') as log:
    child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'user-launcher.py'),str(userroot),*arguments],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    save('capture-'+name,client_pid=child.pid);code=child.wait(timeout=370 if sustained else 100)
   text=(case/'client.log').read_text(errors='replace')
   assert code==0 and 'FIXTURE_RESTORATION result=0' in text,text[-3500:]
   identities=re.findall(r'APPLICATION_IDENTITY uid=(\d+) euid=(\d+) capeff=(\S+)',text)
   assert len(identities)==1 and identities[0][:2]==('10000','10000') and int(identities[0][2],16)==0
   summary=dict(isolated=isolated,uid=uid,effective_capabilities=0,elapsed_seconds=round(time.monotonic()-launched,3),exit_code=code)
   if sustained:
    assert 'GST_RESULT frames=9000 width=1920 height=1080 bus-errors=0 result=0' in text
    summary['frames']=9000;state['sustained'][name]=summary
   else:
    assert 'LIFECYCLE_RESULT cycles=3 manager-starts=1 status=0' in text
    assert len(re.findall(r'LIFECYCLE_END cycle=\d+ status=0',text))==3
    summary.update(cycles=3,frames=text.count('ADAPT_FRAME '));state['captures'][name]=summary
   idle();s=status();summary['ipe_completed']=s['completed']-before
   assert summary['frames']<=summary['ipe_completed']<=summary['frames']+(1 if sustained else 3)
   assert not any(s[k] for k in ['failed','cancelled','first_error','fatal'])
  finally:
   if child is not None and child.poll() is None:
    os.killpg(child.pid,signal.SIGTERM)
    try:child.wait(timeout=8)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
   if observer is not None:
    observer.terminate()
    try:observer.wait(timeout=3)
    except subprocess.TimeoutExpired:observer.kill();observer.wait(timeout=3)
    observer_log.close();assert observer.returncode==0
   if (userroot/'captures').exists():shutil.copytree(userroot/'captures',case/'captures')
   assert userroot.resolve().parent==Path('/run/user/10000').resolve() and userroot.name.startswith('k449-user-')
   shutil.rmtree(userroot)
 state['candidate_final_status']=status();state['candidate_final_core']=core();verified=True
