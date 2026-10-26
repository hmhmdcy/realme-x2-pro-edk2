"""Use the deployed driver and existing bundle; keep desktop consumers running."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,time,traceback
root=Path(sys.argv[1]);root.mkdir(mode=0o700)
state={'pid':os.getpid(),'terminal':False,'phase':'preflight'}
def save(): (root/'state.json').write_text(json.dumps(state,indent=2)+'\n')
def consumers():
    values={}
    for p in Path('/proc').glob('[0-9]*'):
        try:
            name=(p/'comm').read_text().strip()
            if name in ['pipewire','wireplumber']:values[name]=int(p.name)
        except FileNotFoundError:pass
    return values
save();failure=None;captures={}
before=subprocess.check_output(['dmesg']);before_consumers=consumers()
try:
    if Path('/proc/sys/kernel/random/boot_id').read_bytes()!=Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes():raise RuntimeError('Device restarted')
    if hashlib.sha256(Path('/sys/module/qcom_camss/notes/.note.gnu.build-id').read_bytes()).hexdigest()!=sys.argv[2]:raise RuntimeError('Different CAMSS is loaded')
    stage=Path('/var/lib/samurai/k309-cameras-r3/bundle')
    for model in ['imx319','s5k3m5']:
        state.update(phase='capturing',sensor=model);save()
        env=dict(os.environ,LD_LIBRARY_PATH=str(stage/'lib'),CAMSS_AWB_EPOCHS='1',CAMSS_AE_ENABLE='1',
                 LIBCAMERA_CAMSS_VFE_ENABLE='1',LIBCAMERA_PIPELINES_MATCH_LIST='camss-vfe',
                 LIBCAMERA_CAMSS_VFE_PROFILE=str(stage/'profile'/(model+'.yaml')),
                 LIBCAMERA_IPA_MODULE_PATH=str(stage/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(stage/'proxy'),
                 LIBCAMERA_IPA_FORCE_ISOLATION='1',LIBCAMERA_LOG_LEVELS='*:WARN,CamssVfe:DEBUG,IPACamss:DEBUG')
        q=subprocess.run([str(stage/'bin/pipeline-fixture'),'/dev/media0',str(stage/'bin/camera-smoke'),model],
                         env=env,capture_output=True,timeout=62)
        text=(q.stdout+q.stderr).decode(errors='replace');(root/('capture-'+model+'.log')).write_text(text)
        captures[model]={'exit':q.returncode,'image_frames':text.count('APPLICATION_FRAME '),
                         'fixture_restored':'FIXTURE_RESTORATION result=0' in text}
        if q.returncode:raise RuntimeError(model+' capture failed')
except BaseException:
    failure=traceback.format_exc();(root/'failure.txt').write_text(failure)
finally:
    for _ in range(30):
        status=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip()
        if status=='suspended':break
        time.sleep(.2)
    after=subprocess.check_output(['dmesg'])
    faults={w.decode():after.count(w)-before.count(w) for w in [b'WARNING:',b'Oops:',b'gpu fault:',b'fatal error received',b'CCI error']}
    report={'stage':309,'automatic_exposure_and_awb':True,'deployed_module_reused':True,
            'consumers_unchanged':before_consumers==consumers(),'captures':captures,
            'failure':failure is not None,'fault_delta':faults,'camss_runtime':status,
            'taint':int(Path('/proc/sys/kernel/tainted').read_text())}
    report['passed']=not report['failure'] and report['consumers_unchanged'] and len(captures)==2 and all(
        v['exit']==0 and v['fixture_restored'] for v in captures.values()) and not any(faults.values()) and not report['taint'] and status=='suspended'
    state.update(terminal=True,phase='complete' if report['passed'] else 'failed',summary=report);save()
    print(json.dumps(report))
