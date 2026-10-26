"""Run independent cameras under one temporary CAMSS load and restore once."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel308/native-capture.py').read_text()
s=s.replace("tele=len(sys.argv)>2 and sys.argv[2]=='tele'\nepochs_wanted=1 if len(sys.argv)>3 and sys.argv[3]=='single' else 2",
"""models=sys.argv[2].split(',')
automatic=sys.argv[3]=='joint'
if not models or not set(models)<={'s5kgw1','imx471','imx319','s5k3m5'}:raise ValueError('camera')
captures={}
verify_raw=len(sys.argv)>4 and sys.argv[4]=='raw'
raw_captures={}""")
a=s.index("    save('capturing')")
b=s.index('except BaseException:',a)
s=s[:a]+'''    stage=root/'bundle'
    for model in models:
        save('capturing',sensor=model)
        env=dict(os.environ,LD_LIBRARY_PATH=str(stage/'lib'),CAMSS_AWB_EPOCHS='1',
                 CAMSS_AE_ENABLE='1' if automatic else '0',LIBCAMERA_CAMSS_VFE_ENABLE='1',
                 LIBCAMERA_PIPELINES_MATCH_LIST='camss-vfe',
                 LIBCAMERA_CAMSS_VFE_PROFILE=str(stage/'profile'/(model+'.yaml')),
                 LIBCAMERA_IPA_MODULE_PATH=str(stage/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(stage/'proxy'),
                 LIBCAMERA_IPA_FORCE_ISOLATION='1',
                 LIBCAMERA_LOG_LEVELS='*:WARN,CamssVfe:DEBUG,IPACamss:DEBUG,IPAManager:DEBUG,IPAProxy:DEBUG')
        label='capture-'+model
        try:
            run([str(stage/'bin/pipeline-fixture'),'/dev/media0',str(stage/'bin/camera-smoke'),model],
                label,timeout=62,env=env)
            captures[model]=0
        except RuntimeError:
            captures[model]=1
            text=(root/(label+'.log')).read_text(errors='replace')
            if 'FIXTURE_RESTORATION result=0' not in text:raise
        wait_idle()
        if verify_raw:
            devices=[p for p in Path('/sys/bus/i2c/drivers',model).iterdir()
                     if p.is_symlink() and re.fullmatch(r'\\d+-[0-9a-f]{4}',p.name)]
            if len(devices)!=1:raise RuntimeError('Missing sensor device')
            camera_id='/base'+str((devices[0]/'of_node').resolve()).split('/base',1)[1]
            raw_env=dict(os.environ,LIBCAMERA_PIPELINES_MATCH_LIST='simple',
                         LIBCAMERA_SOFTISP_USE_GPU='0',LIBCAMERA_LOG_LEVELS='*:WARN')
            run([str(stage/'bin/pipeline-fixture'),'/dev/media0','/usr/sbin/cam',
                 '-c',camera_id,'--capture=4'],'raw-'+model,timeout=62,env=raw_env)
            raw_text=(root/('raw-'+model+'.log')).read_text(errors='replace')
            raw_captures[model]={'frames':len(re.findall(r'seq:\\s*\\d+',raw_text)),
                                 'fixture_restored':'FIXTURE_RESTORATION result=0' in raw_text}
            wait_idle()
'''+s[b:]
a=s.index("    text=(root/'capture.log')")
s=s[:a]+'''    summaries={}
    for model in models:
        p=root/('capture-'+model+'.log')
        text=p.read_text(errors='replace') if p.exists() else ''
        epochs=[dict(epoch=int(e),frames=int(f),failed=int(x),stop=int(y))
                for e,f,x,y in re.findall(r'APPLICATION_EPOCH epoch=(\\d+) frames=(\\d+) failed=(\\d+) stop=(-?\\d+)',text)]
        summaries[model]={'exit':captures.get(model),'image_frames':text.count('APPLICATION_FRAME '),
                         'epochs':epochs,'fixture_restored':'FIXTURE_RESTORATION result=0' in text,
                         'isolation_forced':'forced through configuration' in text,
                         'locked_frames':len(re.findall(r'APPLICATION_WB .* locked=1',text))}
    report={'stage':309,'automatic_exposure_and_awb':automatic,'failure':failure is not None,
            'deployment_restored':restored,'captures':summaries,'fault_delta':faults,
            'taint':int(Path('/proc/sys/kernel/tainted').read_text()),
            'temporary_module_only':True,'installed_files_unchanged':True,'raw_captures':raw_captures}
    report['passed']=not report['failure'] and restored and not any(faults.values()) and not report['taint'] and all(
        r['exit']==0 and r['fixture_restored'] and len(r['epochs'])==1 and not r['epochs'][0]['failed']
        for r in summaries.values())
    if verify_raw:report['passed']=report['passed'] and len(raw_captures)==len(models) and all(
        r['frames']==4 and r['fixture_restored'] for r in raw_captures.values())
    save('complete' if report['passed'] else 'failed',terminal=True,summary=report)
    print(json.dumps(report))
'''
(HERE/'native-capture.py').write_text(s)
print('Prepared multi-camera worker with one CAMSS load per run.')
