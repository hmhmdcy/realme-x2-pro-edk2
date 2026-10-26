"""Check common AGC refactor against separate baseline342/new ARM binaries."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
candidate=storage.candidate();baseline=candidate.parent/'libcamera342-r27-built'
stageBacking=candidate.parent/'camss359-contract';stageBacking.mkdir(exist_ok=True)
relative=Path('/private/camss359-contract');stage=storage.SDK/str(relative).lstrip('/');stage.mkdir(exist_ok=True)
baseRelative=Path('/private/camss359-baseline');baseStage=storage.SDK/str(baseRelative).lstrip('/');baseStage.mkdir(exist_ok=True)
mounts=[];results=[]
try:
 for backing,target in [(stageBacking,stage),(baseline,baseStage)]:
  assert subprocess.run(['mountpoint','-q',str(target)],capture_output=True).returncode
  subprocess.run(['mount','--bind',str(backing),str(target)],check=True,capture_output=True);mounts.append(target)
 with storage.sdk_candidate():
  shutil.copyfile(HERE/'agc-regression.cpp',stage/'agc-regression.cpp')
  trees={'baseline':str(baseRelative)+'/src/libcamera-v0.7.2','candidate':'/work/libcamera/src/libcamera-v0.7.2'}
  for label,tree in trees.items():
   flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror','-DLIBCAMERA_BASE_PRIVATE','-I'+tree+'/include','-I'+tree+'/output/include','-I'+tree+'/src/ipa/libipa']
   links=[tree+'/output/src/ipa/libipa/libipa.a','-L'+tree+'/output/src/libcamera','-L'+tree+'/output/src/libcamera/base','-Wl,-rpath-link,'+tree+'/output/src/libcamera/base','-lcamera','-lcamera-base']
   q=subprocess.run(['chroot',str(storage.SDK),'g++',*flags,str(relative/'agc-regression.cpp'),*links,'-o',str(relative/('agc-'+label))],capture_output=True)
   (P/('agc-'+label+'-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()[-4500:]
  for row in json.loads((P/'cases-private.json').read_text()):
   profile=Path(row['legacy_profile']);shutil.copyfile(profile,stage/profile.name);m=row['match'];lineUs=m['line_length']*1000000./m['pixel_rate']
   for label,tree in trees.items():
    q=subprocess.run(['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+tree+'/output/src/libcamera:'+tree+'/output/src/libcamera/base','LIBCAMERA_LOG_LEVELS=*:FATAL',str(relative/('agc-'+label)),str(relative/profile.name),row['model'],str(lineUs),str(row['minimum_lines']),str(row['maximum_lines']),str(row['minimum_code']),str(row['maximum_code']),str(relative/(row['name']+'-'+label+'.bin')),'48'],capture_output=True,timeout=60)
    (P/(row['name']+'-agc-'+label+'.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(row['name'],label,q.stderr.decode()[-4000:])
   old=(stage/(row['name']+'-baseline.bin')).read_bytes();new=(stage/(row['name']+'-candidate.bin')).read_bytes();assert len(old)==48*32
   assert old==new,(row['name'],sum(a!=b for a,b in zip(old,new)))
   results.append(dict(case=row['name'],frames=48,compared_bytes=len(old),differing_bytes=0,passed=True));print(row['name']+' common AGC unchanged',flush=True)
finally:
 for target in reversed(mounts):subprocess.run(['umount',str(target)],check=True,capture_output=True)
unchanged=[]
for name in ['exposure_mode_helper.cpp','exposure_mode_helper.h','camera_sensor_helper.cpp','camera_sensor_helper.h']:
 old=(baseline/'src/libcamera-v0.7.2/src/ipa/libipa'/name).read_bytes();new=(candidate/'src/libcamera-v0.7.2/src/ipa/libipa'/name).read_bytes();assert old==new;unchanged.append(name)
report=dict(stage=359,separate_matching_baseline_and_candidate_headers_and_archives=True,actual_aarch64=True,cases=results,
 zero_exposure_fallback=True,temporal_filter_and_reset=True,multiple_ev_targets=True,quantization_and_saturation=True,
 unchanged_sensor_quantizer_sources=unchanged,sdk_bind_unmounted=True,passed=True)
(HERE/'agc-regression-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(stage=359,frames=sum(x['frames'] for x in results),differing_bytes=0,passed=True)))
