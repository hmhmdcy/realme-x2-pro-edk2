"""One sensor-only installation with main LSC and normal consumer verification."""
from pathlib import Path
import hashlib,io,json,shlex,subprocess,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
build=json.loads((HERE/'kernel-build-validation.json').read_text());assert build['passed'];module=Path(build['module'])
note=P/'candidate-note.bin';subprocess.run(['aarch64-linux-gnu-objcopy','--dump-section','.note.gnu.build-id='+str(note),str(module),str(P/'note-copy.ko')],check=True)
code='''
from pathlib import Path
import hashlib,json,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k305-geometry-r2/boot-id-private.txt').read_bytes()
target=Path(subprocess.check_output(['modinfo','-n','s5kgw1'],text=True).strip()).resolve()
print(json.dumps(dict(module_path=str(target),old_module_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),old_module_note_sha256=hashlib.sha256(Path('/sys/module/s5kgw1/notes/.note.gnu.build-id').read_bytes()).hexdigest(),
 vermagic=subprocess.check_output(['modinfo','-F','vermagic',str(target)],text=True).strip(),
 taint=int(Path('/proc/sys/kernel/tainted').read_text()),camera_runtime={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']})))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20);baseline=json.loads(q.stdout)
if '--from-color-bars' in sys.argv:
 prior=json.loads((HERE/'install-r2-validation.json').read_text());assert prior['passed']
 oldproof=json.loads((P/'install-r2-proof.json').read_text())
 assert baseline['old_module_sha256']==oldproof['module_sha256'] and baseline['old_module_note_sha256']==oldproof['module_note_sha256']
else:assert baseline['old_module_sha256']=='9f1a060f3fd146b6049635efa165dc2ba3cfa5ac96066085f0a5ada54ef10088'
assert baseline['vermagic']==build['vermagic'] and not baseline['taint'] and all(v=='suspended' for v in baseline['camera_runtime'].values())
proof=dict(stage=325,module_sha256=build['module_sha256'],module_note_sha256=hashlib.sha256(note.read_bytes()).hexdigest(),**baseline)
(P/'install-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
s=(HERE.parent/'kernel318/native-install.py').read_text().replace('stage=318','stage=325').replace("'stage':318","'stage':325").replace('.k318-tmp','.k325-tmp')
s=s.replace('qcom_camss','s5kgw1').replace('qcom-camss','s5kgw1').replace('loaded_camss_note_sha256','loaded_gw1_note_sha256')
s=s.replace('"""Install the tested package/module pair, retaining an offline rollback."""','"""Install the standard GW1 control and verify factory LSC/normal consumers."""')
s=s.replace("model='imx319'","model='s5kgw1'")
s=s.replace('def sha(p):', '''def unbind_sensor():
 if device and (device/'driver').is_symlink():
  if (device/'driver').resolve()!=driver:raise RuntimeError('Unexpected sensor binding')
  (driver/'unbind').write_text(device.name)
def bind_sensor():
 if not (device/'driver').is_symlink():(driver/'bind').write_text(device.name)
 if (device/'driver').resolve()!=driver:raise RuntimeError('Sensor not bound')
def sha(p):''')
s=s.replace("target=None\n", "target=None;device=None;driver=Path('/sys/bus/i2c/drivers/s5kgw1')\n")
s=s.replace(' consumers=services();wait_idle()', ''' devices=[p for p in driver.iterdir() if (p/'of_node').exists()]
 if len(devices)!=1:raise RuntimeError('Original GW1 binding not unique')
 device=Path('/sys/bus/i2c/devices')/devices[0].name
 if sha('/sys/module/s5kgw1/notes/.note.gnu.build-id')!=proof['old_module_note_sha256']:raise RuntimeError('Loaded baseline changed')
 consumers=services();wait_idle()''')
s=s.replace(" run(['rmmod','s5kgw1'],'unload');changed=True", " save('unbinding-sensor');unbind_sensor()\n run(['rmmod','s5kgw1'],'unload');changed=True")
s=s.replace("run(['modprobe','s5kgw1'],'load')", "run(['modprobe','s5kgw1'],'load');bind_sensor()")
s=s.replace("   if changed and Path('/sys/module/s5kgw1').exists():", "   unbind_sensor()\n   if changed and Path('/sys/module/s5kgw1').exists():")
s=s.replace("run(['modprobe','s5kgw1'],'rollback-load')", "run(['modprobe','s5kgw1'],'rollback-load');bind_sensor()")
at=s.index(" model='s5kgw1';devices=")
s=s[:at]+''' cases=json.loads((root/'cases.json').read_text());captures={}
 sensor_nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().startswith('s5kgw1 ')]
 if len(sensor_nodes)!=1:raise RuntimeError('GW1 sensor node not unique')
 sensor='/dev/'+sensor_nodes[0].name
 for name,item in cases.items():
  save('testing-main-lsc',selection=name)
  env=dict(os.environ,LIBCAMERA_CAMSS_VFE_PROFILE=str(root/'profiles'/(item['profile']+'.yaml')),LIBCAMERA_LOG_LEVELS='*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG')
  for key in ['LIBCAMERA_CAMSS_VFE_ENABLE','LIBCAMERA_PIPELINES_MATCH_LIST','LIBCAMERA_IPA_FORCE_ISOLATION','LIBCAMERA_IPA_MODULE_PATH']:env.pop(key,None)
  args=[str(root/'pipeline-fixture'),'/dev/media0',str(root/'bin/lsc-smoke'),item['model'],sensor,str(root/(name+'-private.nv12')),item['output'],item['sensor_size'],str(item['test_pattern'])]
  q=run(args,'capture-'+name,timeout=30,env=env);log=(q.stdout+q.stderr).decode(errors='replace')
  passed=' failed=0 result=0' in log and 'FIXTURE_RESTORATION result=0' in log and 'LSC_PATTERN index=2 maximum=2 name=Shade Color Bars' in log and 'LSC_PATTERN_ACTIVE toggled=1' in log and ('lsc='+str(int(item['lsc']))) in log
  captures[name]=dict(frames=log.count('LSC_IMAGE '),settled=log.count('settled=1'),passed=passed)
  if not passed:raise RuntimeError(name+' main LSC capture failed')
 wait_idle()
'''+s[at:]
s=s.replace('user_probe=None\n','user_probe=None;captures={}\n')
s=s.replace('loaded_gw1_note_sha256=sha(', 'captures=captures,loaded_gw1_note_sha256=sha(')
s=s.replace(" report['services']={name:"," report['rails']={(p/'name').read_text().strip():{'state':(p/'state').read_text().strip(),'users':int((p/'num_users').read_text())} for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))}\n report['services']={name:")
s=s.replace(" and all(len(value)==1 for value in report['services'].values())"," and all(len(value)==1 for value in report['services'].values()) and all(value=={'state':'disabled','users':0} for value in report['rails'].values())")
(HERE/'native-install.py').write_text(s)
files={'worker.py':HERE/'native-install.py','proof.json':P/'install-proof.json','s5kgw1.ko':module,'cases.json':HERE/'cases.json',
 'pipeline-fixture':P.parent/'kernel313/pipeline-fixture','bin/lsc-smoke':SDK/'private/camss325-runtime/lsc-smoke',
 'bin/gst-hardware-probe':SDK/'private/camss316-runtime/gst-hardware-probe','bin/pw-hardware-probe':SDK/'private/camss316-runtime/pw-hardware-probe'}
for p in (P/'profiles').glob('*.yaml'):files['profiles/'+p.name]=p
with tarfile.open(P/'install.tar.gz','w:gz') as tar:
 for name,p in files.items():
  raw=p.read_bytes();item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o700 if name.startswith('bin/') or name=='pipeline-fixture' else 0o600;tar.addfile(item,io.BytesIO(raw))
for name in ['launch-install.py']:
 s=(HERE.parent/'kernel318'/name).read_text().replace('k318-install-','k325-install-').replace('stage=318','stage=325').replace('tested_module_loaded','tested_sensor_module_loaded')
 # The collector below is customized separately; observe without --collect.
 (HERE/name).write_text(s)
print(json.dumps(dict(stage=325,candidate=module.name,cases=len(json.loads((HERE/'cases.json').read_text())),baseline_idle=True,packages_or_image_not_changed=True),indent=2))
