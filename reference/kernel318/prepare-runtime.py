"""Prepare a temporary-module LSC experiment with restoration in finally."""
from pathlib import Path
import io,json,tarfile
import host
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel316/native-temp-probe.py').read_text()
a=s.index('    for selection in models:');b=s.index('\nexcept BaseException:',a)
s=s[:a]+'''    for selection in models:
        save('capturing',selection=selection)
        env=dict(os.environ,LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG')
        for key in ['LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_IPA_FORCE_ISOLATION','LIBCAMERA_CAMSS_VFE_PROFILE']:env.pop(key,None)
        if selection=='pattern':
            app=[str(root/'bin/samurai-lsc'),'--pattern',str(root/'pattern-private')]
        else:
            devices=[p for p in Path('/sys/bus/i2c/drivers',selection).iterdir() if (p/'of_node').exists()]
            camera_id='/base'+str((devices[0]/'of_node').resolve()).split('/base',1)[1]
            app=[str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/gst-hardware-probe'),camera_id,'640','480']
        with (root/('capture-'+selection+'.log')).open('xb') as log:
            child=subprocess.Popen(app,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            save('capturing',selection=selection,child_pid=child.pid)
            try:ret=child.wait(timeout=40)
            except subprocess.TimeoutExpired:
                child.send_signal(signal.SIGINT);ret=child.wait(timeout=10)
        text=(root/('capture-'+selection+'.log')).read_text(errors='replace')
        expected='CAPTURE_RESULT success=1 cleanup_complete=1' if selection=='pattern' else 'bus-errors=0 result=0'
        if ret or expected not in text:raise RuntimeError(selection+' capture failed')
'''+s[b:]
a=s.index('    report=dict(stage=316,');b=s.index("    save('complete'",a)
s=s[:a]+'''    report=dict(stage=318,failure=failure is not None,deployment_restored=restored,
     captures={m:{'frames':t.count('LSC_FRAME ')+t.count('GST_IMAGE '),
       'probe_passed':('CAPTURE_RESULT success=1 cleanup_complete=1' in t) if m=='pattern' else ('bus-errors=0 result=0' in t),
       'settled_phases':t.count('settled=1'),
       'cleanup_restored':('cleanup_complete=1' in t) if m=='pattern' else ('FIXTURE_RESTORATION result=0' in t)} for m,t in captures.items()},
     fault_delta=faults,taint=int(Path('/proc/sys/kernel/tainted').read_text()),health=health,
     temporary_module_only=True,installed_files_unchanged=True)
    report['passed']=not report['failure'] and restored and all(c['probe_passed'] and c['cleanup_restored'] for c in report['captures'].values()) and not any(faults.values()) and not report['taint'] and all(v=='suspended' for v in health['platforms'].values()) and all(v=={'state':'disabled','users':0} for v in health['rails'].values())
'''+s[b:]
(HERE/'native-probe.py').write_text(s)
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
build=json.loads((HERE/'kernel-build-validation.json').read_text());assert build['exit_code']==0
files={'qcom-camss.ko':Path(build['module']),'worker.py':HERE/'native-probe.py',
 'pipeline-fixture':host.PRIVATE.parent/'kernel313/pipeline-fixture',
 'bin/samurai-lsc':host.PRIVATE/'samurai-lsc',
 'bin/gst-hardware-probe':SDK/'private/camss316-runtime/gst-hardware-probe'}
with tarfile.open(host.PRIVATE/'probe.tar.gz','w:gz') as tar:
 for name,p in files.items():
  raw=p.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700 if name.startswith('bin/') or name=='pipeline-fixture' else 0o600
  tar.addfile(item,io.BytesIO(raw))
for name in ['launch-temp-probe.py','poll-temp-probe.py']:
 t=(HERE.parent/'kernel316'/name).read_text().replace('k316-consumer-','k318-lsc-').replace('consumer-','probe-')
 (HERE/name.replace('-temp','')).write_text(t)
print('Prepared LSC pattern and installed-stack camera probes.')
