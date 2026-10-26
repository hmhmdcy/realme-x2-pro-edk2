"""Package the 315 userspace with the already tested 314 CAMSS module."""
from pathlib import Path
import io,json,tarfile
import host
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel313'
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');TREE=SDK/'work/libcamera299-inline'
s=(HERE.parent/'kernel314/native-probe.py').read_text()
s=s.replace('    for p in Path(\'/proc/asound\').glob(\'card*/pcm*/sub*/status\'):\n        if p.read_text().strip()!=\'closed\': raise RuntimeError(\'Audio is in use\')\n','')
a=s.index('    for index,model in enumerate(models):');b=s.index('\nexcept BaseException:',a)
s=s[:a]+'''    for selection in models:
        model,kind=selection.split(':')
        env=dict(os.environ,LD_LIBRARY_PATH=str(root/'lib'),
                 LIBCAMERA_CAMSS_VFE_ENABLE='1',LIBCAMERA_PIPELINES_MATCH_LIST='camss-vfe',
                 LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(root/'proxy'),
                 LIBCAMERA_IPA_CONFIG_PATH=str(root/'profile'),LIBCAMERA_IPA_FORCE_ISOLATION='1',
                 LIBCAMERA_LOG_LEVELS='*:WARN,CamssVfe:DEBUG,IPACamss:DEBUG')
        label=selection.replace(':','-')
        save('capturing',selection=selection)
        with (root/('capture-'+label+'.log')).open('xb') as log:
            child=subprocess.Popen([str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/raw-smoke'),model,kind],
                  env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            save('capturing',selection=selection,child_pid=child.pid)
            try:ret=child.wait(timeout=55 if kind.startswith('af') else 24)
            except subprocess.TimeoutExpired:
                child.send_signal(signal.SIGINT);ret=child.wait(timeout=10)
        text=(root/('capture-'+label+'.log')).read_text(errors='replace')
        if ret or 'RAW_RESULT ' not in text or 'FIXTURE_RESTORATION result=0' not in text:raise RuntimeError(selection+' capture failed')
'''+s[b:]
s=s.replace("captures={model:(root/('capture-'+model+'.log')).read_text(errors='replace') if (root/('capture-'+model+'.log')).exists() else '' for model in models}",
 "captures={model:(root/('capture-'+model.replace(':','-')+'.log')).read_text(errors='replace') if (root/('capture-'+model.replace(':','-')+'.log')).exists() else '' for model in models}")
s=s.replace('stage=314','stage=315').replace("t.count('DUAL_FRAME ')","t.count('RAW_IMAGE ')").replace("'DUAL_RESULT success=1' in t", "'RAW_RESULT ' in t and 'failed=0 result=0' in t")
(HERE/'native-probe.py').write_text(s)
build=json.loads((HERE.parent/'kernel314/kernel-build-validation.json').read_text());assert build['exit_code']==0
assert json.loads((HERE/'build-validation.json').read_text())['exit_code']==0
files={'qcom-camss.ko':Path(build['module']),'pipeline-fixture':host.PRIVATE.parent/'kernel313/pipeline-fixture',
 'worker.py':HERE/'native-probe.py','bin/raw-smoke':SDK/'private/camss315-runtime/raw-smoke',
 'lib/libcamera.so.0.7':TREE/'output/src/libcamera/libcamera.so.0.7.2',
 'lib/libcamera-base.so.0.7':TREE/'output/src/libcamera/base/libcamera-base.so.0.7.2',
 'ipa/ipa_camss_vfe.so':TREE/'output/src/ipa/camss-vfe/ipa_camss_vfe.so',
 'ipa/ipa_camss_vfe.so.sign':TREE/'output/src/ipa/camss-vfe/ipa_camss_vfe.so.sign',
 'proxy/camss_ipa_proxy':TREE/'output/src/libcamera/proxy/worker/camss_ipa_proxy'}
files.update({'profile/camss-vfe/'+m+'.yaml':OLD/(m+'.yaml') for m in ['s5kgw1','imx471','imx319','s5k3m5']})
with tarfile.open(host.PRIVATE/'probe.tar.gz','w:gz') as tar:
 for name,path in files.items():
  raw=path.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw)
  item.mode=0o700 if name=='pipeline-fixture' or name.startswith(('bin/','proxy/')) else 0o600
  tar.addfile(item,io.BytesIO(raw))
print('Packaged315 handler with unchanged314 kernel and313 IPA/profiles.')
