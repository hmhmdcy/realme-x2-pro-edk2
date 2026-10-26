"""Bounded phone-side measurement body; importing performs no device action."""
from pathlib import Path
import hashlib,json,os,pwd,re,runpy,shutil,subprocess,time

COMMON=None
def common(root):
    global COMMON
    if COMMON is None:COMMON=runpy.run_path(str(Path(root)/'capture-common-private.py'))
    return COMMON
def validate_handoff(root,state):
    plan=common(root)['validate_handoff'](root,state)
    assert os.uname().release==plan['expected_uname']['release']
    assert os.uname().version==plan['expected_uname']['version']
    return plan
def finalize(root,state):return common(root)['finalize'](root,state)

def witness(logfile,userroot,plan,helpers):
    text=logfile.read_text(errors='replace')
    app=set(map(int,re.findall(r'APPLICATION_PROCESS pid=(\d+)',text)))
    ipa=set(map(int,re.findall(r'IPA stats pid=(\d+)',text)))
    step=set(map(int,re.findall(r'STEPPER_READY pid=(\d+)',text)))
    if not all(len(v)==1 for v in [app,ipa,step]):return None
    ap,ip,sp=[next(iter(v)) for v in [app,ipa,step]];assert len({ap,ip,sp})==3
    records=[]
    for pid,name in [(ap,'delay-capture-mode2-aarch64'),(ip,'proxy/camss_ipa_proxy'),(sp,'control-stepper-mode2-aarch64')]:
        proc,start,values=helpers['proc_identity'](pid)
        assert (proc/'exe').resolve()==userroot/name
        assert helpers['sha'](proc/'exe')==plan['common_payload'][name]
        assert all(int(v)==10000 for v in values['Uid'].split()) and int(values['CapEff'],16)==0
        records.append(dict(pid=pid,start_ticks=start,program=name))
    for pid in [ap,ip]:
        maps=Path('/proc',str(pid),'maps').read_text()
        assert str(userroot/'lib/libcamera.so.0.7.2') in maps
    assert str(userroot/'ipa/ipa_camss_vfe.so') in Path('/proc',str(ip),'maps').read_text()
    return dict(processes=records,isolated=True,old461_core_and_proxy=True,passed=True)

def run_tele(root,state,save,status,idle,core):
    root=Path(root);helpers=common(root);plan=json.loads((root/'tele-plan-private.json').read_text())
    assert plan['kind']=='sensor-control-delay' and plan['deployable']
    assert shutil.disk_usage(root).free>=2*1024**3
    account=pwd.getpwuid(10000);userroot=Path('/run/user/10000')/('k449-user-'+root.name)
    assert userroot.parent==Path('/run/user/10000') and root.name.startswith('k476-control-delay-')
    assert not userroot.exists() and not helpers['related'](userroot)
    userroot.mkdir(mode=0o700);child=None;started=time.monotonic();state['captures']={};state['sustained']={}
    try:
        for directory in ['lib','ipa','proxy']:(userroot/directory).mkdir(mode=0o700)
        for relative,digest in plan['common_payload'].items():
            target=userroot/relative;shutil.copyfile(root/relative,target)
            target.chmod(0o700 if relative in ['delay-capture-mode2-aarch64','control-stepper-mode2-aarch64','proxy/camss_ipa_proxy'] else 0o600)
            assert helpers['sha'](target)==digest
        for lib in ['libcamera','libcamera-base']:(userroot/f'lib/{lib}.so.0.7').symlink_to(f'{lib}.so.0.7.2')
        for path in [userroot,*userroot.rglob('*')]:
            if path.is_symlink():os.lchown(path,10000,account.pw_gid)
            else:os.chown(path,10000,account.pw_gid)
        env=dict(os.environ)
        for key in list(env):
            if key=='LD_LIBRARY_PATH' or key.startswith(('LIBCAMERA_','CAPTURE_','GST_','MEASURE_')):env.pop(key,None)
        env.update(LD_LIBRARY_PATH=str(userroot/'lib'),LIBCAMERA_CAMSS_VFE_ENABLE='1',LIBCAMERA_PIPELINES_MATCH_LIST='camss-vfe',
            LIBCAMERA_IPA_MODULE_PATH=str(userroot/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(userroot/'proxy'),
            LIBCAMERA_IPA_FORCE_ISOLATION='1',LIBCAMERA_CAMSS_VFE_PROFILE=str(userroot/'mode2-measurement-private.yaml'),
            LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG',PIPELINE_FIXTURE_TIMEOUT_SECONDS='30',
            MEASURE_KERNEL_RELEASE=plan['expected_uname']['release'],MEASURE_KERNEL_VERSION=plan['expected_uname']['version'])
        logfile=root/'control-capture-private.log';before=status();evidence=None
        with logfile.open('xb') as output:
            child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'user-launcher.py'),str(userroot),
                'delay-capture-mode2-aarch64','s5k3m5',str(userroot/'control-stepper-mode2-aarch64')],env=env,
                stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
            save('control-capturing',client_pid=child.pid)
            while child.poll() is None and time.monotonic()-started<15 and evidence is None:
                evidence=witness(logfile,userroot,plan,helpers)
                if evidence is None:time.sleep(.01)
            assert evidence and evidence['passed'],'Actual capture/stepper/isolated IPA witness required'
            (root/'control-live-witness-private.json').write_text(json.dumps(evidence,indent=2)+'\n')
            code=child.wait(timeout=max(1,50-(time.monotonic()-started)))
        text=logfile.read_text(errors='replace')
        assert code==0 and 'FIXTURE_RESTORATION result=0' in text
        frames=re.findall(r'APPLICATION_EPOCH epoch=0 frames=(\d+) failed=0 stop=0',text)
        assert len(frames)==1 and int(frames[0])>=240
        frame_count=int(frames[0])
        assert 'APPLICATION_RESULT result=0' in text and 'STEPPER_RESULT result=0 events=233 steps=9' in text
        assert 'STEPPER_INITIAL_READBACK exposure=500 gain_code=64' in text and 'delayed-controls=0' in text
        assert len(re.findall(r'STEPPER_MODE width=4208 height=2368 code=\d+ crop=0,376,4208,2368 hblank=640 vblank=944 pixel_rate=481930000 test_pattern=0',text))==2
        assert len(re.findall(r'CONTROL_WRITE .* ret=0 errno=0',text))==9
        assert len(re.findall(r'Pair epoch=1 sof=\d+ request=\d+ population=2491136 mean=[\d.e+-]+ parameter-buffer-submitted=1',text))==frame_count
        idle();after=status()
        assert after['completed']==before['completed'],'Measurement profile must not schedule IPE jobs'
        assert not any(after[k] for k in ['failed','cancelled','first_error','fatal'])
        state['control_capture']=dict(frames=frame_count,steps=9,exit_code=code,actual_sensor=[4208,2368],
            expected_ll=4848,expected_fll=3312,linear_bhist_population=2491136,isolated=True,live_witness=True,
            no_delayed_controls=True,no_ae_profile=True,delay_result_not_preset=True,ipe_jobs=0)
        save('control-capture-complete')
    finally:
        if child is not None and child.poll() is None:child.wait(timeout=max(1,60-(time.monotonic()-started)))
        deadline=time.monotonic()+6
        while helpers['related'](userroot) and time.monotonic()<deadline:time.sleep(.05)
        assert not helpers['related'](userroot),'Never remove a live client directory'
        assert userroot.parent==Path('/run/user/10000') and userroot.name=='k449-user-'+root.name
        shutil.rmtree(userroot)
