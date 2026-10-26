"""Create the one-module install worker using the already tested lifecycle."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
text=(HERE/'native-capture.py').read_text()
tree=ast.parse(text)
helpers='\n\n'.join(ast.get_source_segment(text,n) for n in tree.body if isinstance(n,ast.FunctionDef)
                   and n.name in ['save','run','processes','services','wait_idle'])
body=r'''
root=Path(sys.argv[1])
state={'pid':os.getpid(),'terminal':False,'phase':'preflight'}
marker=root/'state.json'
if marker.exists():raise RuntimeError('Install already started; inspect it')
proof=json.loads((root/'proof.json').read_text())
stopped=[];consumers={};verified=False;rollback=False;failure=None;restart_failure=None
target=None;backup=root/'qcom-camss-before.ko'
before=subprocess.check_output(['dmesg'])
save('preflight')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def replace(source):
    tmp=target.with_name(target.name+'.k309-tmp')
    shutil.copyfile(source,tmp);tmp.chmod(0o644);os.replace(tmp,target)
try:
    if Path('/proc/sys/kernel/random/boot_id').read_bytes()!=Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes():raise RuntimeError('Device restarted')
    if Path('/proc/sys/kernel/tainted').read_text().strip()!='0':raise RuntimeError('Unexpected taint')
    target=Path(subprocess.check_output(['modinfo','-n','qcom_camss'],text=True).strip()).resolve()
    expected=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/platform/qcom/camss/qcom-camss.ko'
    if target!=expected or sha(target)!=proof['old_sha256']:raise RuntimeError('Unexpected deployed module')
    if sha(root/'qcom-camss.ko')!=proof['module_sha256']:raise RuntimeError('Candidate differs from tested module')
    for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'):
        if p.read_text().strip()!='closed':raise RuntimeError('Audio is in use')
    consumers=services();shutil.copyfile(target,backup);wait_idle()
    save('stopping-consumers')
    for name in ['wireplumber','pipewire']:
        fd=os.pidfd_open(consumers[name]['pid'])
        try:
            signal.pidfd_send_signal(fd,signal.SIGTERM)
            if not select.select([fd],[],[],8)[0]:raise RuntimeError(name+' did not exit')
        finally:os.close(fd)
        stopped.append(name)
    save('replacing-module');run(['rmmod','qcom_camss'],'unload')
    replace(root/'qcom-camss.ko');run(['depmod','-a'],'depmod',timeout=30)
    run(['modprobe','qcom_camss'],'load')
    if sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')!=proof['module_note_sha256']:raise RuntimeError('Loaded module differs')
    run(['cam','-l'],'enumeration')
    devices=[p for p in Path('/sys/bus/i2c/drivers/imx471').iterdir()
             if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name)]
    camera_id='/base'+str((devices[0]/'of_node').resolve()).split('/base',1)[1]
    env=dict(os.environ,LIBCAMERA_PIPELINES_MATCH_LIST='simple',LIBCAMERA_SOFTISP_USE_GPU='0')
    q=run([str(root/'pipeline-fixture'),'/dev/media0','/usr/sbin/cam','-c',camera_id,'--capture=4'],
          'raw-smoke',timeout=62,env=env)
    text=(q.stdout+q.stderr).decode(errors='replace')
    if len(re.findall(r'seq:\s*\d+',text))!=4 or 'FIXTURE_RESTORATION result=0' not in text:raise RuntimeError('RAW smoke did not restore')
    wait_idle()
    if sha(target)!=proof['module_sha256']:raise RuntimeError('Installed file differs')
    verified=True;save('module-verified')
except BaseException:
    failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
    if not verified and backup.exists() and target:
        try:
            save('rollback')
            if Path('/sys/module/qcom_camss').exists():run(['rmmod','qcom_camss'],'rollback-unload')
            replace(backup);run(['depmod','-a'],'rollback-depmod',timeout=30)
            run(['modprobe','qcom_camss'],'rollback-load')
            rollback=sha(target)==proof['old_sha256']
        except BaseException:(root/'rollback-failure.txt').write_text(traceback.format_exc())
    if verified or rollback or not stopped:
        try:
            for name in ['pipewire','wireplumber']:
                if name not in stopped:continue
                item=consumers[name];user=pwd.getpwuid(item['uid'])
                def demote():
                    os.initgroups(user.pw_name,user.pw_gid);os.setgid(user.pw_gid);os.setuid(user.pw_uid)
                env=item['env'].copy();env.pop('PIPEWIRE_NOTIFICATION_FD',None)
                with (root/(name+'-restart.log')).open('wb') as output:
                    child=subprocess.Popen(item['argv'],env=env,cwd=item['cwd'],preexec_fn=demote,
                        stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
                time.sleep(.5)
                if child.poll() is not None:raise RuntimeError('Consumer restart failed')
            wait_idle()
        except BaseException:restart_failure=traceback.format_exc();(root/'restart-failure.txt').write_text(restart_failure)
    after=subprocess.check_output(['dmesg'])
    faults={w.decode():after.count(w)-before.count(w) for w in [b'WARNING:',b'Oops:',b'gpu fault:',b'fatal error received',b'CCI error']}
    report={'stage':309,'module_installed':verified,'rollback':rollback,'failure':failure is not None,
            'restart_failure':restart_failure is not None,'fault_delta':faults,
            'taint':int(Path('/proc/sys/kernel/tainted').read_text()),
            'module_sha256':sha(target) if target and target.exists() else None}
    report['passed']=verified and not report['failure'] and not report['restart_failure'] and not any(faults.values()) and not report['taint']
    save('complete' if report['passed'] else 'failed',terminal=True,summary=report)
    print(json.dumps(report))
'''
header='from pathlib import Path\nimport hashlib,json,os,pwd,re,select,signal,shutil,subprocess,sys,time,traceback\n\n'
(HERE/'native-install.py').write_text(header+helpers+'\n\n'+body)
print('Prepared focused persistent CAMSS module transaction.')
