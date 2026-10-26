from pathlib import Path
import difflib,hashlib,json,shutil
import storage
HERE=Path(__file__).resolve().parent;library=storage.candidate()/'src/libcamera-v0.7.2';baseline=storage.previous.candidate()/'src/libcamera-v0.7.2'
for leaf in ['camss_ipe.cpp','camss_ipe.h']:shutil.copyfile(HERE/leaf,library/'src/libcamera/pipeline/camss-vfe'/leaf)
patch=''
for leaf in ['camss_vfe.cpp','camss_ipe.h','camss_ipe.cpp','meson.build']:
 relative=Path('src/libcamera/pipeline/camss-vfe')/leaf;prior=baseline/relative;current=library/relative
 a=prior.read_text() if prior.exists() else '';b=current.read_text()
 patch+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+str(relative) if a else '/dev/null',tofile='b/'+str(relative)))
(HERE/'camss-ipe-pipeline.patch').write_text(patch)
state=json.loads((HERE/'source-state.json').read_text());state['ipe_wrapper_sha256']=hashlib.sha256((HERE/'camss_ipe.cpp').read_bytes()).hexdigest();(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Refreshed wrapper and final library patch; both formats precede allocation.')
