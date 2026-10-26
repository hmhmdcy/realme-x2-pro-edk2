from pathlib import Path
import difflib,hashlib,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;volume=storage.mount.mounted_build().parent
old=volume/'libcamera447-focus-execution';new=storage.candidate();assert old.is_dir()
if new.exists():
 prior=HERE/'source-state.json'
 if prior.exists():
  checkpoint=json.loads(prior.read_text());assert checkpoint['stage']==448 and checkpoint['build_pending'] and not (HERE/'build-validation.json').exists()
 else:checkpoint=json.loads((HERE.parent/'kernel447/source-state.json').read_text())
 for row in checkpoint['source_hashes']:
  assert hashlib.sha256((new/'src/libcamera-v0.7.2'/row['path']).read_bytes()).hexdigest()==row['sha256']
else:shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[s for s in n if s=='pkg' or s.startswith('pkg-before') or s=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';header='src/libcamera/pipeline/camss-vfe/thread_capacity.h';pipeline='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
shutil.copyfile(HERE/'thread_capacity.h',tree/header)
original=(old/'src/libcamera-v0.7.2'/pipeline).read_text();text=original
def replace(a,b):
 global text
 a=a.lstrip(' \t');b=b.lstrip(' \t')
 assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b)
replace('#include "hardware_focus.h"','#include "hardware_focus.h"\n#include "thread_capacity.h"')
replace('LumaFocusWorkspace focusWorkspace_;','LumaFocusWorkspace focusWorkspace_;\n ThreadCapacityLease focusCapacity_;')
replace('  d->running_ = true;', '''  if(d->lensActive_){
   const auto capacity=d->focusCapacity_.acquire();
   LOG(CamssVfe,Debug)<<"CAPACITY_START epoch="<<d->epoch_<<" tid="<<capacity.tid<<" status="<<capacity.status
    <<" reason="<<capacity.reason<<" active="<<capacity.active<<" users="<<capacity.users
    <<" original="<<ThreadCapacityLease::maskString(capacity.original)<<" selected="<<ThreadCapacityLease::maskString(capacity.selected);
  }
  d->running_ = true;''')
replace('  d->focusWorkspace_.clear();','''  {
   const auto capacity=d->focusCapacity_.release();
   LOG(CamssVfe,Debug)<<"CAPACITY_STOP epoch="<<d->epoch_<<" tid="<<capacity.tid<<" status="<<capacity.status
    <<" reason="<<capacity.reason<<" active="<<capacity.active<<" users="<<capacity.users
    <<" original="<<ThreadCapacityLease::maskString(capacity.original)<<" selected="<<ThreadCapacityLease::maskString(capacity.selected);
  }
  d->focusWorkspace_.clear();''')
(tree/pipeline).write_text(text)
patch=''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='a/'+pipeline,tofile='b/'+pipeline))
patch+=''.join(difflib.unified_diff([], (tree/header).read_text().splitlines(True),fromfile='/dev/null',tofile='b/'+header))
(HERE/'0060-camss-stream-thread-capacity-lease.patch').write_text(patch)
state=json.loads((HERE.parent/'kernel447/source-state.json').read_text())
for row in state['source_hashes']:row['sha256']=hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()
state['source_hashes'].append(dict(path=header,sha256=hashlib.sha256((tree/header).read_bytes()).hexdigest()))
state.update(stage=448,source=str(tree),baseline_stage=447,source_baseline_stage=447,changed_this_stage=[header,pipeline],build_pending=True,diagnostic_only=False,stream_lifetime_capacity_lease=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(dict(stage=448,source=str(tree),private_ipa_version=6,phone_changed=False,passed=True)))
