"""Bounded existing-mode tele consumers; importing performs no device action."""
from pathlib import Path
import hashlib,importlib.util,json,os,pwd,re,runpy,shutil,stat,subprocess,time

COMMON=None
def common(root):
    global COMMON
    if COMMON is None:COMMON=runpy.run_path(str(Path(root)/'capture-common-private.py'))
    return COMMON
def validate_handoff(root,state):return common(root)['validate_handoff'](root,state)
def finalize(root,state):return common(root)['finalize'](root,state)

def trace_functions(root):
    # Preserve the reviewed constructor, including evidence basename == plan.name.
    path=Path(root)/'capture-trace-base.py'
    spec=importlib.util.spec_from_file_location('trace461_for467',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def witness(logfile,userroot,plan,trace_helper,role,helpers):
    text=logfile.read_text(errors='replace')
    app=set(map(int,re.findall(r'APPLICATION_PROCESS pid=(\d+)',text)))
    ipa=set(map(int,re.findall(r'IPA stats pid=(\d+)',text)))
    if len(app)!=1 or len(ipa)!=1:return None
    pid=next(iter(app));worker_pid=next(iter(ipa));assert pid!=worker_pid
    process,start,_=helpers['proc_identity'](pid)
    worker,worker_start,_=helpers['proc_identity'](worker_pid)
    assert (process/'exe').resolve()==userroot/'gst-sustained'
    assert helpers['sha'](process/'exe')==plan['common_payload']['gst-sustained']
    expected_core=str(userroot/'lib/libcamera.so.0.7.2')
    assert expected_core in (process/'maps').read_text()
    maps=(worker/'maps').read_text()
    assert expected_core in maps and str(userroot/'ipa/ipa_camss_vfe.so') in maps
    assert (worker/'exe').resolve()==userroot/'proxy/camss_ipa_proxy'
    assert helpers['sha'](worker/'exe')==plan['common_payload']['proxy/camss_ipa_proxy']
    identity=dict(pid=pid,start_ticks=start,exe_sha256=helpers['sha'](process/'exe'),uid=10000,cap_eff=0)
    fds=[]
    for fd in (process/'fd').iterdir():
        try:
            metadata=fd.stat()
            if stat.S_ISCHR(metadata.st_mode):fds.append(dict(fd=int(fd.name),target=os.readlink(fd),major=os.major(metadata.st_rdev),minor=os.minor(metadata.st_rdev)))
        except FileNotFoundError:pass
    assert helpers['proc_identity'](pid)[1]==start and helpers['proc_identity'](worker_pid)[1]==worker_start
    observation=dict(identity=identity,same_process_before_after=True,character_fds=fds)
    proof=trace_helper.role.check_open_fd(role,observation,identity)
    return dict(application=identity,ipa_pid=worker_pid,ipa_start_ticks=worker_start,isolated=True,
                core_mapping_verified=True,actual_ipa_mapping_verified=True,full_fd_observation=observation,**proof,passed=True)

def run_tele(root,state,save,status,idle,core):
    root=Path(root);helpers=common(root);plan=json.loads((root/'tele-plan-private.json').read_text())
    handoff=json.loads((root/'handoff-private.json').read_text())
    assert shutil.disk_usage(root).free>=2*1024**3
    state['captures']={};state['sustained']={}
    nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith('s5k3m5 ')]
    devices=[p for p in Path('/sys/bus/i2c/drivers/s5k3m5').iterdir() if (p/'of_node').exists()]
    assert len(nodes)==len(devices)==1
    camera_id='/base'+str((devices[0]/'of_node').resolve()).split('/base',1)[1]
    account=pwd.getpwuid(10000);userroot=Path('/run/user/10000')/('k449-user-'+root.name)
    trace_helper,session,trace_plan,role=trace_functions(root).start_trace(root,helpers,handoff)
    state['trace_instance']=trace_plan.instance;state['full_role']=role;save('trace-started')
    try:
        for width,height in [(1280,720)]:
            name=f'{width}x{height}-isolated';case=root/name;case.mkdir()
            assert not userroot.exists() and not helpers['related'](userroot)
            userroot.mkdir(mode=0o700);child=None;launched=time.monotonic()
            try:
                for directory in ['lib','ipa','proxy','captures']:(userroot/directory).mkdir(mode=0o700)
                for relative,digest in plan['common_payload'].items():
                    target=userroot/relative;shutil.copyfile(root/relative,target)
                    target.chmod(0o700 if relative in ['gst-sustained','proxy/camss_ipa_proxy'] else 0o600)
                    assert helpers['sha'](target)==digest
                for library in ['libcamera','libcamera-base']:(userroot/f'lib/{library}.so.0.7').symlink_to(f'{library}.so.0.7.2')
                for path in [userroot,*userroot.rglob('*')]:
                    if path.is_symlink():os.lchown(path,10000,account.pw_gid)
                    else:os.chown(path,10000,account.pw_gid)
                env=dict(os.environ)
                for variable in list(env):
                    if variable=='LD_LIBRARY_PATH' or variable.startswith(('LIBCAMERA_','CAPTURE_','GST_')):env.pop(variable,None)
                env.update(LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG',LD_LIBRARY_PATH=str(userroot/'lib'),
                    LIBCAMERA_IPA_MODULE_PATH=str(userroot/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(userroot/'proxy'),
                    LIBCAMERA_CAMSS_VFE_PROFILE=str(userroot/'factory-s5k3m5-private.yaml'),LIBCAMERA_IPA_FORCE_ISOLATION='1',
                    LIBCAMERA_CAMSS_VFE_TRACE_DIR=str(userroot/'captures'),CAPTURE_DIR=str(userroot/'captures'),PIPELINE_FIXTURE_TIMEOUT_SECONDS='30',GST_TARGET_FRAMES='32',
                    GST_SENSOR_NODE='/dev/'+nodes[0].name)
                before=status()['completed'];logfile=case/'client.log'
                with logfile.open('xb') as output:
                    child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'user-launcher.py'),str(userroot),
                        'gst-sustained',camera_id,str(width),str(height)],env=env,stdin=subprocess.DEVNULL,
                        stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
                    save('capture-'+name,client_pid=child.pid);evidence=None
                    while evidence is None and child.poll() is None and time.monotonic()-launched<15:
                        evidence=witness(logfile,userroot,plan,trace_helper,role,helpers)
                        if evidence is None:time.sleep(.01)
                    assert evidence and evidence['passed'],'Required actual application/isolated IPA/FULL FD witness missing'
                    (case/'live-witness-private.json').write_text(json.dumps(evidence,indent=2)+'\n')
                    code=child.wait(timeout=max(1,40-(time.monotonic()-launched)))
                text=logfile.read_text(errors='replace')
                assert code==0 and 'FIXTURE_RESTORATION result=0' in text
                assert f'GST_RESULT frames=32 width={width} height={height} bus-errors=0 result=0' in text
                sensor=re.findall(r'GST_SENSOR width=(\d+) height=(\d+) code=(\d+)',text)
                assert len(sensor)==1 and sensor[0][:2]==('4208','2368') and int(sensor[0][2])>0
                assert re.findall(r'APPLICATION_IDENTITY uid=(\d+) euid=(\d+) capeff=(\S+)',text)==[('10000','10000','0000000000000000')]
                idle();current=status();assert not any(current[k] for k in ['failed','cancelled','first_error','fatal'])
                completed=current['completed']-before;assert 32<=completed<=40
                state['sustained'][name]=dict(width=width,height=height,isolated=True,uid=10000,effective_capabilities=0,
                    frames=32,ipe_completed=completed,exit_code=code,elapsed_seconds=round(time.monotonic()-launched,3),
                    live_full_fd_witness=True,actual_sensor=[4208,2368],sensor_mbus_code=int(sensor[0][2]),intentional_cancellation=False)
            finally:
                if child is not None and child.poll() is None:child.wait(timeout=max(1,45-(time.monotonic()-launched)))
                deadline=time.monotonic()+6
                while helpers['related'](userroot) and time.monotonic()<deadline:time.sleep(.05)
                assert not helpers['related'](userroot),'Preserve directory and process evidence; never blindly signal leftovers'
                if (userroot/'captures').exists():shutil.copytree(userroot/'captures',case/'captures')
                assert not userroot.is_symlink() and userroot.resolve().parent==Path('/run/user/10000').resolve()
                assert userroot.name=='k449-user-'+root.name
                shutil.rmtree(userroot)
    finally:
        session.stop_read();session.cleanup();state['trace_cleaned']=True
    trace=(root/trace_plan.name/'trace-private-1.txt').read_text(errors='replace')
    events=[dict(event='v4l2_'+kind,minor=int(minor)) for kind,minor in re.findall(r'\bv4l2_(qbuf|dqbuf):[^\n]*?\bminor\s*=\s*(\d+)',trace)]
    state['full_emission']=trace_helper.role.check_emission(role,events)
    run_replay(root,state,save,status,idle)
    state['candidate_final_status']=status();state['candidate_final_core']=core()


def sampled_hash(raw):
    value=1469598103934665603
    for byte in raw[::max(1,len(raw)//4096)]:value=((value^byte)*1099511628211)&((1<<64)-1)
    return value

def run_replay(root,state,save,status,idle):
    import fcntl
    source=root/'1280x720-isolated';text=(source/'client.log').read_text(errors='replace')
    records=re.findall(r'IPE_TONE_TRACE epoch=(\d+) sof=(\d+) token=(\d+) revision=(\d+) full-sequence=(\d+) pd10-sequence=(\d+) result=(-?\d+)',text)
    assert len(records)==1 and records[0][-1]=='0'
    epoch,sof,token,revision,full,pd10,result=map(int,records[0]);assert sof==full==pd10 and sof>=12 and revision>0
    case=root/'1280x720-replay';case.mkdir()
    for target,suffix,length in [('full-private.bin','-full.nv12',1382400),('pd10-private.bin','-coarse.pd10',123648),('parameters-private.bin','-params.bin',6008)]:
        path=source/'captures'/f'tone-{sof}{suffix}';assert path.stat().st_size==length;shutil.copyfile(path,case/target)
    video=[str(Path('/dev')/p.parent.name) for p in Path('/sys/class/video4linux').glob('video*/name') if p.read_text().strip()=='qcom-ipe-a5']
    media=[]
    for path in Path('/dev').glob('media[0-9]*'):
        try:
            with path.open('rb',buffering=0) as f:
                data=bytearray(256);fcntl.ioctl(f.fileno(),0xc1007c00,data,True)
            if bytes(data[16:48]).split(bytes([0]))[0]==b'SM8150 IPE':media.append(str(path))
        except OSError:continue
    assert len(video)==len(media)==1
    before=status()['completed']
    with (case/'client.log').open('xb') as log:
        child=subprocess.Popen([str(root/'pd10-ipe'),video[0],media[0],str(case),'1280','720','121008'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        save('replay-1280x720',client_pid=child.pid);code=child.wait(timeout=55)
    text_replay=(case/'client.log').read_text(errors='replace');assert code==0 and 'PD10_IPE_RESULT result=0 frames=4' in text_replay
    outputs=[(case/f'mode-{i}-output-private.bin').read_bytes() for i in range(4)]
    assert all(len(x)==1382400 for x in outputs)
    assert outputs[0]==outputs[3] and len(set(outputs[:3]))==3
    hashes=re.findall(r'GST_IMAGE frame=\d+ width=1280 height=720 bytes=1382400 pts=\d+ hash=(\d+) sequence='+str(sof)+r' wall-ns=\d+',text)
    assert len(hashes)==1 and int(hashes[0])==sampled_hash(outputs[0]),'Actual consumed frame sampling hash differs from real PD10 replay'
    jobs=[json.loads(line) for line in text_replay.splitlines() if line.startswith('{')]
    assert len(jobs)==4 and len({job['full_hash'] for job in jobs})==1 and jobs[0]['pd10_hash']==jobs[3]['pd10_hash'] and len({job['pd10_hash'] for job in jobs[:3]})==3
    idle();current=status();assert current['completed']-before==4 and not any(current[k] for k in ['failed','cancelled','first_error','fatal'])
    state['replays']={'1280x720':dict(width=1280,height=720,source_sof=sof,epoch=epoch,token=token,revision=revision,exit_code=code,
        jobs=jobs,real_input_repeat_byte_equal=True,only_pd10_changes_full_output=True,source_consumed_sample_hash_equal=True,
        source_output_full_byte_compare=False,ipe_completed=4,passed=True)}
