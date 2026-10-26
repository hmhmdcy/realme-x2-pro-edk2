"""Give the media endpoint the same stable identity as its video interface."""
from pathlib import Path
import difflib,hashlib,importlib.util,json,shutil,subprocess
import storage,host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');mount=importlib.util.module_from_spec(spec);spec.loader.exec_module(mount)
build=mount.mounted_build();kernel=build.parent/'source354'
git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a],text=True).strip()
assert git('rev-parse','HEAD')=='ab58f554a7b9f886bd43b9c3f47d52761d9bf982' and not git('status','--porcelain')
header=(kernel/'include/media/media-device.h').read_text();assert 'driver_name[' in header
name='drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c';p=kernel/name;before=p.read_text()
needle='\tdev->media.dev = a5->dev;';assert before.count(needle)==1
after=before.replace(needle,needle+'\n\tstrscpy(dev->media.driver_name, "qcom-ipe-a5", sizeof(dev->media.driver_name));')
git('switch','-c','samurai-ipe-pipeline387');p.write_text(after)
(HERE/'media-driver.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
git('add','--',name);git('commit','-m','media: qcom: expose stable IPE media driver identity')
assert not git('status','--porcelain')
state=json.loads((HERE/'source-state.json').read_text());state.update(commit=git('rev-parse','HEAD'),branch=git('branch','--show-current'),kernel_parent='ab58f554a7b9f886bd43b9c3f47d52761d9bf982',kernel_change='media_driver_identity_only',kernel_unchanged=False)
library=storage.candidate()/'src/libcamera-v0.7.2';p=library/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';s=p.read_text();assert s.count('DeviceMatch ipeMatch("SM8150 IPE")')==1
s=s.replace('DeviceMatch ipeMatch("SM8150 IPE")','DeviceMatch ipeMatch("qcom-ipe-a5")');p.write_text(s);(HERE/'camss-vfe-after.cpp').write_text(s)
state['pipeline_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
script=(HERE.parent/'kernel386/build-intree.py').read_text().replace('stage=386','stage=387')
(HERE/'build-intree.py').write_text(script)
shutil.copyfile(P.parent/'kernel386/live-overlay-state-private.json',P/'live-overlay-state-private.json')
# Refresh the final distributable library patch against the unchanged r29 base.
patch='';baseline=storage.previous.candidate()/'src/libcamera-v0.7.2'
for leaf in ['camss_vfe.cpp','camss_ipe.h','camss_ipe.cpp','meson.build']:
 relative=Path('src/libcamera/pipeline/camss-vfe')/leaf;prior=baseline/relative;current=library/relative
 a=prior.read_text() if prior.exists() else '';b=current.read_text()
 patch+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+str(relative) if a else '/dev/null',tofile='b/'+str(relative)))
(HERE/'camss-ipe-pipeline.patch').write_text(patch)
print(json.dumps(state))
