"""Build an AF probe using normal automatic exposure/gain in the public camera API."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
R=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');name='af-native278-auto'
s=(R/'af-native278-r2.cpp').read_text()
old='''        controls.set(controls::AeEnable, false);
        controls.set(controls::ExposureTimeMode, controls::ExposureTimeModeManual);
        controls.set(controls::AnalogueGainMode, controls::AnalogueGainModeManual);
        controls.set(controls::ExposureTime, 32000);
        controls.set(controls::AnalogueGain, 1.0f);'''
new='''        controls.set(controls::AeEnable, automaticMode);
        controls.set(controls::ExposureTimeMode, automaticMode ? controls::ExposureTimeModeAuto : controls::ExposureTimeModeManual);
        controls.set(controls::AnalogueGainMode, automaticMode ? controls::AnalogueGainModeAuto : controls::AnalogueGainModeManual);
        if (!automaticMode) {
            controls.set(controls::ExposureTime, 32000);
            controls.set(controls::AnalogueGain, 1.0f);
        }'''
assert s.count(old)==1;s=s.replace(old,new).replace('if (index >= 12)','if (index >= 12 && !automaticMode)')
(R/(name+'.cpp')).write_text(s);source=SDK/'private'/(name+'.cpp');assert not source.exists()
source.write_text(s.replace('#include "focus_stats.h"','#include "focus278-stats-r2.h"'))
prefix='/candidate278-r24'
q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+prefix+'/usr/include/libcamera','/private/'+source.name,'-L'+prefix+'/usr/lib','-Wl,-rpath-link,'+prefix+'/usr/lib','-lcamera','-lcamera-base','-o','/private/'+name],capture_output=True,timeout=180)
(host.PRIVATE/'ae-af-probe-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
target=host.PRIVATE/name;shutil.copyfile(SDK/'private'/name,target)
d=dict(stage=278,binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_sha256=hashlib.sha256((R/(name+'.cpp')).read_bytes()).hexdigest(),
 cpp20_werror_clean=True,public_libcamera_controls_only=True,automatic_exposure_and_gain=True,no_application_search_or_lens_writes=True)
(R/'ae-af-probe-build-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
