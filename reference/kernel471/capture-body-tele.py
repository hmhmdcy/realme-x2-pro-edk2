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
    proxy_hash=helpers['sha'](worker/'exe');assert proxy_hash==plan['common_payload']['proxy/camss_ipa_proxy']
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
                proxy_exe_sha256=proxy_hash,core_mapping_verified=True,actual_ipa_mapping_verified=True,full_fd_observation=observation,**proof,passed=True)

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
        assert [v['name'] for v in plan['segments']]==['A1-old','B-new','A2-old']
        for segment in plan['segments']:
            width,height=1920,1080
            name=segment['name'];case=root/name;case.mkdir()
            selected_plan=dict(plan);selected_plan['common_payload']=dict(plan['common_payload'])
            selected_plan['common_payload']['proxy/camss_ipa_proxy']=segment['proxy_sha256']
            assert not userroot.exists() and not helpers['related'](userroot)
            userroot.mkdir(mode=0o700);child=None;launched=time.monotonic()
            try:
                for directory in ['lib','ipa','proxy','captures']:(userroot/directory).mkdir(mode=0o700)
                for relative,digest in selected_plan['common_payload'].items():
                    target=userroot/relative;source=root/(segment['proxy_payload'] if relative=='proxy/camss_ipa_proxy' else relative);shutil.copyfile(source,target)
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
                    LIBCAMERA_CAMSS_FULL_TRACE_DIR=str(userroot/'captures'),CAPTURE_DIR=str(userroot/'captures'),PIPELINE_FIXTURE_TIMEOUT_SECONDS='30',GST_TARGET_FRAMES='32',
                    GST_SENSOR_NODE='/dev/'+nodes[0].name)
                before=status()['completed'];logfile=case/'client.log'
                with logfile.open('xb') as output:
                    child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'user-launcher.py'),str(userroot),
                        'gst-sustained',camera_id,str(width),str(height)],env=env,stdin=subprocess.DEVNULL,
                        stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
                    save('capture-'+name,client_pid=child.pid);evidence=None
                    while evidence is None and child.poll() is None and time.monotonic()-launched<15:
                        evidence=witness(logfile,userroot,selected_plan,trace_helper,role,helpers)
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
                ring=re.findall(r'FULL_OWNERSHIP_TRACE epoch=(\d+) file=(\S+) total=(\d+) retained=(\d+) overwritten=(\d+) result=(-?\d+)',text)
                assert len(ring)==1 and ring[0][-2:]==('0','0') and int(ring[0][2])==int(ring[0][3])>0
                assert len(list((userroot/'captures').glob('full-*.csv')))==1
                idle();current=status();assert not any(current[k] for k in ['failed','cancelled','first_error','fatal'])
                completed=current['completed']-before;assert 32<=completed<=40
                state['sustained'][name]=dict(width=width,height=height,isolated=True,uid=10000,effective_capabilities=0,
                    kind=segment['kind'],proxy_sha256=segment['proxy_sha256'],frames=32,ipe_completed=completed,exit_code=code,elapsed_seconds=round(time.monotonic()-launched,3),
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
    state['candidate_final_status']=status();state['candidate_final_core']=core()
