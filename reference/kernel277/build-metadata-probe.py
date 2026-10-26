"""Build same-request RAW recomputation versus standard FocusFoM metadata."""
from pathlib import Path
import hashlib,json,shutil,subprocess
import host
R=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');name='focus-metadata277'
s=(R/'focus-raw277.cpp').read_text()
old='        out << "]}";';new='''        out << "],\\\"metadata_focus_fom\\\":";
        if (auto value = request->metadata().get(controls::FocusFoM)) out << *value;
        else out << "null";
        out << '}';'''
assert s.count(old)==1;s=s.replace(old,new)
old='require(camera->configure(config.get()) == 0, "configure paired streams");'
assert s.count(old)==1;s=s.replace(old,old+'\n        require(camera->controls().count(&controls::FocusFoM) == 1, "standard FocusFoM advertised");')
(R/(name+'.cpp')).write_text(s)
header=SDK/'private/focus277-metadata-stats.h';assert not header.exists();header.write_bytes((R/'focus_stats.h').read_bytes())
source=SDK/'private'/(name+'.cpp');assert not source.exists();source.write_text(s.replace('#include "focus_stats.h"','#include "focus277-metadata-stats.h"'))
prefix='/candidate277-r23'
q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I'+prefix+'/usr/include/libcamera','/private/'+source.name,'-L'+prefix+'/usr/lib','-Wl,-rpath-link,'+prefix+'/usr/lib','-lcamera','-lcamera-base','-o','/private/'+name],capture_output=True,timeout=180)
(host.PRIVATE/'metadata-probe-build-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,(q.stdout+q.stderr).decode()
target=host.PRIVATE/name;shutil.copyfile(SDK/'private'/name,target)
d=dict(stage=277,binary_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),source_sha256=hashlib.sha256((R/(name+'.cpp')).read_bytes()).hexdigest(),
 focus_helper_sha256=hashlib.sha256((R/'focus_stats.h').read_bytes()).hexdigest(),cpp20_werror_clean=True,
 public_libcamera_api=True,standard_focus_metadata_required=True,same_request_raw_score_recomputed=True)
(R/'metadata-probe-build-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d))
