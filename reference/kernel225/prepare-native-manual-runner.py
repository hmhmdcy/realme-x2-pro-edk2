from pathlib import Path

here=Path(__file__).resolve().parent
text=(here.parent/'kernel223/native-control-runner.py').read_text()
for a,b in [('k223-baseline','k225-baseline'),("'k223-capture-'","'k225-capture-'"),('stage=223','stage=225'),('samurai-camera223-r8','samurai-camera225-r12'),("tag=f'control-snapshot-","tag=f'manual-controls-"),('/run/samurai-camera223-probes/paired-frame-probe','/run/samurai-camera225-probes/manual-control-probe'),('process.communicate(timeout=25)','process.communicate(timeout=90)')]:text=text.replace(a,b)
# Disable core files and retain a useful summary even if the application exits early.
text=text.replace('import fcntl,hashlib,json,os,pwd,re,signal,struct,subprocess,sys,time','import fcntl,hashlib,json,os,pwd,re,signal,struct,subprocess,sys,time,resource\nresource.setrlimit(resource.RLIMIT_CORE,(0,0))')
old="maps=Path('/proc',str(process.pid),'maps').read_text()\n    candidate_libraries_verified=all(str(prefix/'usr/lib'/name) in maps for name in ['libcamera.so.0.7.2','libcamera-base.so.0.7.2'])"
new="maps=''\n    try:maps=Path('/proc',str(process.pid),'maps').read_text()\n    except FileNotFoundError:pass\n    candidate_libraries_verified=all(str(prefix/'usr/lib'/name) in maps for name in ['libcamera.so.0.7.2','libcamera-base.so.0.7.2'])"
assert text.count(old)==1;text=text.replace(old,new)
text=text.replace("frames=data['frames'] if data else [],","frames=data['frames'] if data else [],manual_test_passed=data['passed'] if data else False,manual_phases=data['phases'] if data else 0,")
compile(text,'native-manual-runner.py','exec');(here/'native-manual-runner.py').write_text(text)
print('Reversible native manual-control runner prepared; not executed.')
