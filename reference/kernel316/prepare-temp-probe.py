"""Test packaged runtime files with a temporary module before installation."""
from pathlib import Path
import io,json,tarfile
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
s=(HERE.parent/'kernel315/native-probe.py').read_text()
a=s.index('    for selection in models:');b=s.index('\nexcept BaseException:',a)
s=s[:a]+'''    for selection in models:
        model,kind=selection.split(':')
        base=root/'prefix/usr'
        env=dict(os.environ,LD_LIBRARY_PATH=str(base/'lib'),
                 LIBCAMERA_IPA_MODULE_PATH=str(base/'lib/libcamera/ipa'),
                 LIBCAMERA_IPA_PROXY_PATH=str(base/'libexec/libcamera'),
                 LIBCAMERA_IPA_CONFIG_PATH=str(base/'share/libcamera/ipa'),
                 GST_PLUGIN_PATH_1_0=str(base/'lib/gstreamer-1.0'),GST_REGISTRY=str(root/'registry.bin'),
                 LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG')
        for key in ['LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_IPA_FORCE_ISOLATION','LIBCAMERA_CAMSS_VFE_PROFILE']:env.pop(key,None)
        devices=[p for p in Path('/sys/bus/i2c/drivers',model).iterdir() if (p/'of_node').exists()]
        camera_id='/base'+str((devices[0]/'of_node').resolve()).split('/base',1)[1]
        app=[str(root/'bin/raw-smoke'),model,'raw'] if kind=='raw' else [str(root/'bin/gst-hardware-probe'),camera_id,*kind.split('x')]
        label=selection.replace(':','-')
        save('capturing',selection=selection)
        with (root/('capture-'+label+'.log')).open('xb') as log:
            child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',*app],env=env,
                  stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            save('capturing',selection=selection,child_pid=child.pid)
            try:ret=child.wait(timeout=24)
            except subprocess.TimeoutExpired:
                child.send_signal(signal.SIGINT);ret=child.wait(timeout=10)
        text=(root/('capture-'+label+'.log')).read_text(errors='replace')
        if ret or 'FIXTURE_RESTORATION result=0' not in text or 'for pipeline handler camss-vfe' not in text:raise RuntimeError(selection+' capture failed')
'''+s[b:]
s=s.replace('stage=315','stage=316').replace("t.count('RAW_IMAGE ')","t.count('RAW_IMAGE ')+t.count('GST_IMAGE ')")
s=s.replace("'RAW_RESULT ' in t and 'failed=0 result=0' in t", "('RAW_RESULT ' in t and 'failed=0 result=0' in t) or ('GST_RESULT ' in t and 'bus-errors=0 result=0' in t)")
(HERE/'native-temp-probe.py').write_text(s)
build=json.loads((HERE.parent/'kernel314/kernel-build-validation.json').read_text());assert build['exit_code']==0
assert json.loads((HERE/'package-artifact-validation.json').read_text())['new_ipa_present']
files={'qcom-camss.ko':Path(build['module']),'pipeline-fixture':host.PRIVATE.parent/'kernel313/pipeline-fixture','worker.py':HERE/'native-temp-probe.py',
 'bin/gst-hardware-probe':SDK/'private/camss316-runtime/gst-hardware-probe',
 'bin/raw-smoke':SDK/'private/camss315-runtime/raw-smoke'}
with tarfile.open(host.PRIVATE/'probe.tar.gz','w:gz') as tar:
 for name,path in files.items():
  raw=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700 if name=='pipeline-fixture' or name.startswith('bin/') else 0o600
  tar.addfile(item,io.BytesIO(raw))
 prefix=host.PRIVATE/'package-prefix'
 for p in sorted(prefix.rglob('*')):
  tar.add(p,arcname='prefix/'+p.relative_to(prefix).as_posix(),recursive=False)
print('Prepared packaged316 consumer runtime, without pipeline-enabling environment overrides.')
