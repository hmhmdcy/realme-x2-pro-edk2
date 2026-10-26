"""Definitions for the bounded 461 lifecycle window; importing is inert."""
from pathlib import Path
import hashlib,importlib.util,json,os,pwd,re,runpy,secrets,shutil,stat,subprocess,time

COMMON=None
def common(root):
    global COMMON
    if COMMON is None:COMMON=runpy.run_path(str(Path(root)/'capture-common-private.py'))
    return COMMON
def validate_handoff(root,state):return common(root)['validate_handoff'](root,state)
def finalize(root,state):return common(root)['finalize'](root,state)

def start_trace(root,helpers,handoff):
    spec=importlib.util.spec_from_file_location('guarded_trace461',root/'kernel463/guarded-trace.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    paths=[p for p in [Path('/sys/kernel/tracing'),Path('/sys/kernel/debug/tracing')] if (p/'available_events').is_file()]
    assert paths,'Do not mount or change global tracing'
    trace=paths[0];available=set((trace/'available_events').read_text().split())
    before=helpers['charging']();assert before==handoff['charging']
    probe=dict(tracefs=str(trace),tracing_on=(trace/'tracing_on').read_text().strip(),trace_clock=(trace/'trace_clock').read_text().strip(),
        instances_supported=(trace/'instances').is_dir(),existing_instances=sorted(p.name for p in (trace/'instances').iterdir()),
        wanted_events={name:name in available for name in helper.base.EVENTS},
        formats={name:(trace/'events'/name.replace(':','/')/'format').read_text() for name in helper.base.EVENTS if name in available},
        video_nodes={p.name:dict(name=(p/'name').read_text().strip(),dev=(p/'dev').read_text().strip()) for p in Path('/sys/class/video4linux').glob('video*')},
        interrupts=Path('/proc/interrupts').read_text(),online_cpus=Path('/sys/devices/system/cpu/online').read_text().strip(),
        charging_before=before,charging_after=helpers['charging'](),phone_changed=False)
    extra=dict(cmdline=Path('/proc/cmdline').read_text(),meminfo=Path('/proc/meminfo').read_text(),
        buffer_size_kb=(trace/'buffer_size_kb').read_text(),buffer_total_size_kb=(trace/'buffer_total_size_kb').read_text(),
        online_cpus=probe['online_cpus'],phone_changed=False)
    graphs=[]
    for media in sorted(Path('/dev').glob('media[0-9]*')):
        assert media.is_char_device()
        result=subprocess.run(['media-ctl','-p','-d',str(media)],capture_output=True,timeout=5)
        assert result.returncode==0
        graphs.append(result.stdout)
    graph=b'\n'.join(graphs);packed=helper.base.packed
    probe_bytes=packed(probe);extra_bytes=packed(extra)
    role=helper.role.discover(probe_bytes,graph,'msm_vfe0_pix')
    matches=re.findall(r'^\s*(\d+):[^\n]*\bacb3000\.camss_msm_vfe0\b',probe['interrupts'],re.M)
    assert len(matches)==1,'Determine actual PIX IRQ before enabling the instance'
    token=secrets.token_hex(16)
    selection=dict(schema='samurai-k459-trace-selection-v1',probe_sha256=hashlib.sha256(probe_bytes).hexdigest(),
        extra_sha256=hashlib.sha256(extra_bytes).hexdigest(),tracefs=str(trace),clock='mono',
        instance='k459-full-461-'+token[:10],ownership_token=token,full_video_node=role['full_video_node'],full_minor=role['minor'],
        vfe_irq=int(matches[0]),vfe_irq_action='acb3000.camss_msm_vfe0',pixel_entity=role['pixel_entity'],
        full_role_graph_sha256=hashlib.sha256(graph).hexdigest())
    for name,raw in [('probe-private.json',probe_bytes),('extra-private.json',extra_bytes),('graph-private.txt',graph),
                     ('selection-private.json',packed(selection))]:
        with (root/name).open('xb') as output:output.write(raw)
    plan=helper.GuardedPlan(probe_bytes,packed(selection),extra_bytes,graph)
    session=helper.Session(plan,helper.RealFiles(),str(root/plan.name))
    session.start()
    return helper,session,plan,role

def witness(logfile,userroot,plan,trace_helper,role,helpers,isolated):
    text=logfile.read_text(errors='replace')
    applications=set(map(int,re.findall(r'ADAPT_PID value=(\d+)',text)))
    workers=set(map(int,re.findall(r'IPA stats pid=(\d+)',text)))
    if len(applications)!=1 or len(workers)!=1:return None
    pid=next(iter(applications));ipa=next(iter(workers))
    assert (pid!=ipa)==isolated
    process,start,_=helpers['proc_identity'](pid)
    exe=(process/'exe').resolve();assert exe==userroot/'lifecycle'
    assert helpers['sha'](exe)==plan['common_payload']['lifecycle']
    expected_core=str(userroot/'lib/libcamera.so.0.7.2')
    assert expected_core in (process/'maps').read_text()
    worker,_,_=helpers['proc_identity'](ipa)
    assert expected_core in (worker/'maps').read_text() and str(userroot/'ipa/ipa_camss_vfe.so') in (worker/'maps').read_text()
    if isolated:
        assert (worker/'exe').resolve()==userroot/'proxy/camss_ipa_proxy'
        assert helpers['sha'](worker/'exe')==plan['common_payload']['proxy/camss_ipa_proxy']
    identity=dict(pid=pid,start_ticks=start,exe_sha256=helpers['sha'](exe),uid=10000,cap_eff=0)
    fds=[]
    for fd in (process/'fd').iterdir():
        try:
            metadata=fd.stat()
            if stat.S_ISCHR(metadata.st_mode):fds.append(dict(fd=int(fd.name),target=os.readlink(fd),major=os.major(metadata.st_rdev),minor=os.minor(metadata.st_rdev)))
        except FileNotFoundError:pass
    assert helpers['proc_identity'](pid)[1]==start
    observation=dict(identity=identity,same_process_before_after=True,character_fds=fds)
    proof=trace_helper.role.check_open_fd(role,observation,identity)
    return dict(application=identity,ipa_pid=ipa,isolated=isolated,core_mapping_verified=True,
                actual_ipa_mapping_verified=True,full_fd_observation=observation,**proof,passed=True)

def run_lifecycle(root,state,save,status,idle,core):
    root=Path(root);helpers=common(root);plan=json.loads((root/'lifecycle-plan-private.json').read_text())
    handoff=json.loads((root/'handoff-private.json').read_text())
    assert shutil.disk_usage(root).free>=2*1024**3
    state['captures']={};state['sustained']={}
    nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith('s5kgw1 ')]
    assert len(nodes)==1
    account=pwd.getpwuid(10000);userroot=Path('/run/user/10000')/('k450-user-'+root.name)
    trace_helper,session,trace_plan,role=start_trace(root,helpers,handoff)
    state['trace_instance']=trace_plan.instance;state['full_role']=role;save('trace-started')
    try:
        for name,isolated in [('user-native',False),('user-isolated',True)]:
            case=root/name;case.mkdir();assert not userroot.exists() and not helpers['related'](userroot)
            userroot.mkdir(mode=0o700);child=None;launched=time.monotonic()
            try:
                for directory in ['lib','ipa','proxy','captures']:(userroot/directory).mkdir(mode=0o700)
                for relative,digest in plan['common_payload'].items():
                    target=userroot/relative;shutil.copyfile(root/relative,target)
                    target.chmod(0o700 if relative in ['lifecycle','proxy/camss_ipa_proxy'] else 0o600)
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
                    LIBCAMERA_CAMSS_VFE_PROFILE=str(userroot/'factory-s5kgw1-private.yaml'),CAPTURE_DIR=str(userroot/'captures'),
                    PIPELINE_FIXTURE_TIMEOUT_SECONDS='70')
                if isolated:env['LIBCAMERA_IPA_FORCE_ISOLATION']='1'
                before=status()['completed'];logfile=case/'client.log'
                with logfile.open('xb') as output:
                    child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'user-launcher.py'),str(userroot),
                        'lifecycle','s5kgw1','/dev/'+nodes[0].name,'4608x2592','0'],env=env,stdin=subprocess.DEVNULL,
                        stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
                    save('capture-'+name,client_pid=child.pid)
                    evidence=None
                    while evidence is None and child.poll() is None and time.monotonic()-launched<15:
                        evidence=witness(logfile,userroot,plan,trace_helper,role,helpers,isolated)
                        if evidence is None:time.sleep(.025)
                    assert evidence and evidence['passed'],'Required real application/IPA/FULL FD witness missing'
                    (case/'live-witness-private.json').write_text(json.dumps(evidence,indent=2)+'\n')
                    code=child.wait(timeout=max(1,85-(time.monotonic()-launched)))
                text=logfile.read_text(errors='replace')
                assert code==0 and 'FIXTURE_RESTORATION result=0' in text and 'LIFECYCLE_RESULT cycles=3 manager-starts=1 status=0' in text
                assert re.findall(r'APPLICATION_IDENTITY uid=(\d+) euid=(\d+) capeff=(\S+)',text)==[('10000','10000','0000000000000000')]
                assert re.findall(r'LIFECYCLE_BEGIN cycle=\d+ output=(\d+x\d+)',text)==['1280x720','1920x1080','1280x720']
                idle();current=status();assert not any(current[k] for k in ['failed','cancelled','first_error','fatal'])
                frames=text.count('ADAPT_FRAME ');completed=current['completed']-before
                assert frames<=completed<=frames+3
                state['captures'][name]=dict(isolated=isolated,uid=10000,effective_capabilities=0,cycles=3,frames=frames,
                    ipe_completed=completed,exit_code=code,elapsed_seconds=round(time.monotonic()-launched,3),live_full_fd_witness=True)
            finally:
                if child is not None and child.poll() is None:child.wait(timeout=max(1,90-(time.monotonic()-launched)))
                deadline=time.monotonic()+6
                while helpers['related'](userroot) and time.monotonic()<deadline:time.sleep(.05)
                assert not helpers['related'](userroot),'Keep user directory; never blindly signal a leftover process'
                if (userroot/'captures').exists():shutil.copytree(userroot/'captures',case/'captures')
                assert not userroot.is_symlink() and userroot.resolve().parent==Path('/run/user/10000').resolve()
                assert userroot.name=='k450-user-'+root.name
                shutil.rmtree(userroot)
    finally:
        session.stop_read();session.cleanup()
        state['trace_cleaned']=True
    trace=(root/trace_plan.name/'trace-private-1.txt').read_text(errors='replace')
    events=[dict(event='v4l2_'+kind,minor=int(minor)) for kind,minor in re.findall(r'\bv4l2_(qbuf|dqbuf):[^\n]*?\bminor\s*=\s*(\d+)',trace)]
    state['full_emission']=trace_helper.role.check_emission(role,events)
    state['candidate_final_status']=status();state['candidate_final_core']=core()
