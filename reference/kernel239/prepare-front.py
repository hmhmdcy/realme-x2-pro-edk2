from pathlib import Path
import ast,json,shutil
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel239')
assert json.loads((R/'r15-startup-analysis.json').read_text())['r15_initial_snapshot_verified']
source=(R.parent/'kernel237/native-capture-r2.py').read_text().replace('stage=237','stage=239').replace("[('rear','raw'),('front','raw'),('front','rgb')]","[('front','raw'),('front','rgb')]").replace("out=root/f'k237-capture-{which}-{kind}-r2'","out=root/f'k239-front-r15-{kind}'").replace('/run/samurai-camera237-probes/native-physical-probe','/run/samurai-camera239-probes/front-physical-probe')
old=" env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR='/run/user/10000',LIBCAMERA_LOG_LEVELS='*:INFO,SimplePipeline:DEBUG')";assert source.count(old)==1
new=" prefix=Path('/run/samurai-camera239-r15');env=dict(PATH='/usr/bin:/bin',HOME=user.pw_dir,XDG_RUNTIME_DIR='/run/user/10000',LIBCAMERA_LOG_LEVELS='*:INFO,SimplePipeline:DEBUG,Debayer:DEBUG',LD_LIBRARY_PATH=str(prefix/'usr/lib'),XDG_CONFIG_HOME=str(prefix/'config-enabled'),LIBCAMERA_IPA_MODULE_PATH=str(prefix/'usr/lib/libcamera/ipa'),LIBCAMERA_IPA_PROXY_PATH=str(prefix/'usr/libexec/libcamera'),LIBCAMERA_IPA_CONFIG_PATH=str(prefix/'usr/share/libcamera/ipa'))"
source=source.replace(old,new).replace('save();process=None;','maps_seen=set();save();process=None;')
old=" state['capture_pid']=process.pid;save()\n try:stdout,stderr=";assert source.count(old)==1
source=source.replace(old,""" state['capture_pid']=process.pid;save()
 for _ in range(12):
  if process.poll() is not None:break
  try:
   for line in Path('/proc',str(process.pid),'maps').read_text().splitlines():
    if '/run/samurai-camera239-r15/' in line:maps_seen.add(line.split()[-1])
  except OSError:pass
  time.sleep(.05)
 (out/'candidate-mapped-files-private.json').write_text(json.dumps(sorted(maps_seen),indent=2)+'\\n')
 try:stdout,stderr=""")
source=source.replace('  sensor_csid_patterns_zero=', "  candidate_core_and_ipa_mapped=all(any('/run/samurai-camera239-r15/usr/lib/'+name in p for p in maps_seen) for name in ['libcamera.so','libcamera-base.so','libcamera/ipa/ipa_soft_simple.so']),\n  sensor_csid_patterns_zero=")
source=source.replace("'camera_devices_suspended','mclk1_mclk2_disabled']", "'camera_devices_suspended','mclk1_mclk2_disabled','candidate_core_and_ipa_mapped']")
ast.parse(source);(R/'native-front.py').write_text(source)
shutil.copyfile(P.parent/'kernel237/native-physical-probe237',P/'front-physical-probe239')
print('Prepared exact front RAW/RGB regression against r15 candidate; original237 probe retained')
