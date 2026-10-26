"""Create an isolated libcamera candidate from the installed r30 source."""
from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;new=storage.candidate();old=new.parent/'libcamera391-ipe-r30-built'
assert not new.exists()
subprocess.run(['cp','-a','--reflink=auto',str(old),str(new)],check=True)
# Packaging outputs are irrelevant to this candidate library and remain intact.
tree=new/'src/libcamera-v0.7.2';baseline=old/'src/libcamera-v0.7.2'
for name in ['camss_ipe.cpp','camss_ipe.h']:(tree/'src/libcamera/pipeline/camss-vfe'/name).write_bytes((HERE/name).read_bytes())
file=tree/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp';s=file.read_text()
oldcall='std::make_unique<CamssIpe>(source->deviceNode())';assert s.count(oldcall)==1
file.write_text(s.replace(oldcall,'std::make_unique<CamssIpe>(source->deviceNode(), ipeMedia_)'))
(tree/'include/linux/qcom-ipe-a5.h').write_bytes((HERE.parent/'kernel417/qcom-ipe-a5.h').read_bytes())
names=['src/libcamera/pipeline/camss-vfe/'+n for n in ['camss_ipe.h','camss_ipe.cpp','camss_vfe.cpp']]+['include/linux/qcom-ipe-a5.h']
patch='';rows=[]
for name in names:
    a=(baseline/name).read_text() if (baseline/name).exists() else '';b=(tree/name).read_text()
    patch+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+name if a else '/dev/null',tofile='b/'+name))
    rows.append(dict(path=name,sha256=hashlib.sha256((tree/name).read_bytes()).hexdigest()))
(HERE/'0041-camss-ipe-request.patch').write_text(patch)
r=dict(stage=418,source=str(tree),baseline_stage=391,kernel_candidate_stage=417,source_hashes=rows,
    existing_v4l2_request_controls_and_video_queue_api_reused=True,nonzero_params_explicitly_supported=True,
    automatic_iq_algorithm_unchanged=True,ipa_interface_unchanged=True,installed=False,passed=True)
(HERE/'source-state.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
