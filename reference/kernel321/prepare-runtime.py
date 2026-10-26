from pathlib import Path
import io,json,shutil,subprocess,tarfile,yaml
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
TREE='/work/libcamera321-lsc-built/src/libcamera-v0.7.2';SRC=SDK/TREE.lstrip('/')
stage=SDK/'private/camss321-runtime';stage.mkdir(exist_ok=True);shutil.copyfile(HERE/'lsc-smoke.cpp',stage/'lsc-smoke.cpp')
q=subprocess.run(['chroot',str(SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include','/private/camss321-runtime/lsc-smoke.cpp','-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o','/private/camss321-runtime/lsc-smoke'],capture_output=True)
(host.PRIVATE/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
profiles=host.PRIVATE/'profiles';profiles.mkdir(exist_ok=True)
base=yaml.safe_load((HERE.parent/'kernel313/imx319.yaml').read_text());mode=base['modes'][0];mode['residual_black_subtraction']=0;mode['range_normalization']=1.
(profiles/'off.yaml').write_text(yaml.safe_dump(base,sort_keys=False))
for name in ['unity','gain','gradient','calibrated']:
 lsc=dict(source_span=[1631.,1223.],first_quad=[0.,0.],quad_step=[2.,2.],gains={})
 for c in ['r','gr','gb','b']:
  lsc['gains'][c]=[1.5 if name=='gain' else 1+x/16+y*.02 if name=='gradient' else 1. for y in range(13) for x in range(17)]
 if name=='calibrated':
  lsc['gains']={c:[b]*221 for c,b in zip(['r','gr','gb','b'],[1.25,1.5,2.,2.25])}
  lsc['golden']={c:[100*f]*221 for c,f in zip(['r','gr','gb','b'],[2,1,.5,1.5])};lsc['unit']={c:[100.]*221 for c in ['r','gr','gb','b']}
 mode['lens_shading']=lsc;(profiles/(name+'.yaml')).write_text(yaml.safe_dump(base,sort_keys=False))
s=(HERE.parent/'kernel318/native-probe.py').read_text().replace('stage=318','stage=321')
a=s.index("    deployed=subprocess.check_output");b=s.index('    wait_idle()',a);s=s[:a]+s[b:]
a=s.index("    save('unloading-deployed')");b=s.index("    save('capturing')",a);s=s[:a]+s[b:]
a=s.index('    for selection in models:');b=s.index('\nexcept BaseException:',a)
s=s[:a]+'''    devices=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith('imx319 ')]
    if len(devices)!=1:raise RuntimeError('IMX319 node not unique')
    sensor='/dev/'+devices[0].name
    for selection in models:
        save('capturing',selection=selection)
        env=dict(os.environ,LIBCAMERA_IPA_MODULE_PATH=str(root/'ipa'),
                 LIBCAMERA_CAMSS_VFE_PROFILE=str(root/'profiles'/(selection+'.yaml')),
                 LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
        for key in ['LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_IPA_FORCE_ISOLATION']:env.pop(key,None)
        app=[str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/lsc-smoke'),'imx319',sensor,str(root/(selection+'-private.nv12'))]
        with (root/('capture-'+selection+'.log')).open('xb') as log:
            child=subprocess.Popen(app,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            save('capturing',selection=selection,child_pid=child.pid)
            try:ret=child.wait(timeout=25)
            except subprocess.TimeoutExpired:child.send_signal(signal.SIGINT);ret=child.wait(timeout=10)
        t=(root/('capture-'+selection+'.log')).read_text(errors='replace')
        if ret or ' failed=0 result=0' not in t or 'FIXTURE_RESTORATION result=0' not in t:raise RuntimeError(selection+' capture failed')
'''+s[b:]
s=s.replace("'frames':t.count('LSC_FRAME ')+t.count('GST_IMAGE ')","'frames':t.count('LSC_IMAGE ')")
s=s.replace("('CAPTURE_RESULT success=1 cleanup_complete=1' in t) if m=='pattern' else ('bus-errors=0 result=0' in t)","(' failed=0 result=0' in t)")
s=s.replace("('cleanup_complete=1' in t) if m=='pattern' else ('FIXTURE_RESTORATION result=0' in t)","('FIXTURE_RESTORATION result=0' in t)")
s=s.replace('temporary_module_only=True,installed_files_unchanged=True','temporary_userspace_only=True,installed_files_unchanged=True')
(HERE/'native-probe.py').write_text(s)
files={'worker.py':HERE/'native-probe.py','pipeline-fixture':host.PRIVATE.parent/'kernel313/pipeline-fixture','bin/lsc-smoke':stage/'lsc-smoke'}
for p in (SRC/'output/src/ipa/camss-vfe').glob('ipa_camss_vfe.so*'):
 if p.is_file():files['ipa/'+p.name]=p
for p in profiles.glob('*.yaml'):files['profiles/'+p.name]=p
with tarfile.open(host.PRIVATE/'probe.tar.gz','w:gz') as tar:
 for name,p in files.items():
  raw=p.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700 if name.startswith('bin/') or name=='pipeline-fixture' else 0o600;tar.addfile(item,io.BytesIO(raw))
for name in ['launch-probe.py','poll-probe.py']:
 s=(HERE.parent/'kernel318'/name).read_text().replace('k318-lsc-','k321-lsc-');(HERE/name).write_text(s)
print('Prepared signed IPA and known synthetic LSC profiles; no module or package change.')
