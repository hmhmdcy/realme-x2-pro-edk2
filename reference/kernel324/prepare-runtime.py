"""Build only a mode-selectable capture tool; use the installed signed r26 IPA."""
from pathlib import Path
import io,json,shutil,subprocess,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');TREE='/work/libcamera321-lsc-built/src/libcamera-v0.7.2'
stage=SDK/'private/camss324-runtime';stage.mkdir(exist_ok=True)
s=(HERE.parent/'kernel321/lsc-smoke.cpp').read_text().replace('#include <cstring>','#include <cstring>\n#include <cstdio>\n#include <linux/v4l2-subdev.h>')
s=s.replace('if(argc!=4)return 2;','''if(argc!=6)return 2;
 unsigned ow=0,oh=0,sw=0,sh=0;
 if(std::sscanf(argv[4],"%ux%u",&ow,&oh)!=2 || std::sscanf(argv[5],"%ux%u",&sw,&sh)!=2 || !ow || !oh || !sw || !sh)return 2;
 const Size requested(ow,oh),sensorRequested(sw,sh);''')
s=s.replace('config->at(0).size=Size(320,240);','''config->at(0).size=requested;
 SensorConfiguration sensorConfig;sensorConfig.bitDepth=10;sensorConfig.outputSize=sensorRequested;
 config->sensorConfig=sensorConfig;''').replace('format.size!=Size(320,240)','format.size!=requested')
s=s.replace('v4l2_control pattern{V4L2_CID_TEST_PATTERN,0};','''v4l2_subdev_format sensorFormat{};sensorFormat.which=V4L2_SUBDEV_FORMAT_ACTIVE;
 if(ioctl(sensor,VIDIOC_SUBDEV_G_FMT,&sensorFormat) || Size(sensorFormat.format.width,sensorFormat.format.height)!=sensorRequested){close(sensor);return 6;}
 std::cout<<"LSC_SENSOR width="<<sensorFormat.format.width<<" height="<<sensorFormat.format.height<<std::endl;
 v4l2_control pattern{V4L2_CID_TEST_PATTERN,0};''')
same_source=(stage/'lsc-smoke.cpp').exists() and (stage/'lsc-smoke.cpp').read_text()==s
(HERE/'lsc-smoke.cpp').write_text(s);(stage/'lsc-smoke.cpp').write_text(s)
if '--repack' in sys.argv:
 assert same_source and (stage/'lsc-smoke').is_file()
else:
 q=subprocess.run(['chroot',str(SDK),'g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+TREE+'/include','-I'+TREE+'/output/include',
  '/private/camss324-runtime/lsc-smoke.cpp','-L'+TREE+'/output/src/libcamera','-L'+TREE+'/output/src/libcamera/base','-Wl,-rpath-link,'+TREE+'/output/src/libcamera/base','-lcamera','-lcamera-base','-pthread','-o','/private/camss324-runtime/lsc-smoke'],capture_output=True)
 (P/'probe-build.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
cases={}
for model,sizes,variants in [('s5kgw1',[(4608,3456),(4608,2592)],['qtech_s5kgw1','sunny_s5kgw1']),('imx471',[(2304,1728),(1928,1088)],['sunny_imx471'])]:
 for i,(w,h) in enumerate(sizes):
  output='320x240' if i==0 else '320x180';tag='4x3' if i==0 else '16x9'
  for profile in [model+'-off',*variants]:
   cases[profile+'-'+tag]=dict(model=model,profile=profile,output=output,sensor_size=f'{w}x{h}',lsc=not profile.endswith('-off'))
(HERE/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
s=(HERE.parent/'kernel322/native-probe.py').read_text().replace('stage=322','stage=324')
begin=s.index('    devices=[p for p in Path');end=s.index('\nexcept BaseException:',begin)
s=s[:begin]+'''    cases=json.loads((root/'cases.json').read_text())
    for selection in models:
        item=cases[selection];model=item['model']
        devices=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith(model+' ')]
        if len(devices)!=1:raise RuntimeError('Sensor node not unique: '+model)
        sensor='/dev/'+devices[0].name
        save('capturing',selection=selection)
        env=dict(os.environ,LIBCAMERA_CAMSS_VFE_PROFILE=str(root/'profiles'/(item['profile']+'.yaml')),
                 LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
        for key in ['LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_IPA_FORCE_ISOLATION','LIBCAMERA_IPA_MODULE_PATH']:env.pop(key,None)
        app=[str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/lsc-smoke'),model,sensor,str(root/(selection+'-private.nv12')),item['output'],item['sensor_size']]
        with (root/('capture-'+selection+'.log')).open('xb') as log:
            child=subprocess.Popen(app,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            save('capturing',selection=selection,child_pid=child.pid)
            try:ret=child.wait(timeout=25)
            except subprocess.TimeoutExpired:child.send_signal(signal.SIGINT);ret=child.wait(timeout=10)
        t=(root/('capture-'+selection+'.log')).read_text(errors='replace')
        expected='lsc='+str(int(item['lsc']))
        if ret or ' failed=0 result=0' not in t or 'FIXTURE_RESTORATION result=0' not in t or expected not in t:raise RuntimeError(selection+' capture failed')
'''+s[end:]
(HERE/'native-probe.py').write_text(s)
files={'worker.py':HERE/'native-probe.py','cases.json':HERE/'cases.json','pipeline-fixture':P.parent/'kernel313/pipeline-fixture','bin/lsc-smoke':stage/'lsc-smoke'}
for p in (P/'profiles').glob('*.yaml'):files['profiles/'+p.name]=p
with tarfile.open(P/'probe.tar.gz','w:gz') as tar:
 for name,p in files.items():
  raw=p.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700 if name.startswith('bin/') or name=='pipeline-fixture' else 0o600;tar.addfile(item,io.BytesIO(raw))
for name in ['launch-probe.py','poll-probe.py','fetch-results.py']:
 s=(HERE.parent/'kernel323'/name).read_text().replace('k323-lsc-','k324-lsc-');(HERE/name).write_text(s)
(HERE/'probe-build-validation.json').write_text(json.dumps(dict(stage=324,aarch64_tool_built=True,werror=True,uses_installed_ipa=True,cases=len(cases),passed=True),indent=2)+'\n')
print('Prepared '+str(len(cases))+' main/front mode/profile cases using installed IPA.')
