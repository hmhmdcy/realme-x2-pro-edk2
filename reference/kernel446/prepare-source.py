"""Reuse a per-camera bounded focus workspace, prepared before streaming."""
from pathlib import Path
import difflib,hashlib,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;volume=storage.mount.mounted_build().parent
old=volume/'libcamera445-focus-grid';new=storage.candidate();assert old.is_dir()
if new.exists():
 assert not (HERE/'source-state.json').exists()
 baseline=json.loads((HERE.parent/'kernel445/source-state.json').read_text())
 assert all(hashlib.sha256((new/'src/libcamera-v0.7.2'/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in baseline['source_hashes'] if not r['path'].endswith('/hardware_focus.h'))
 assert (new/'src/libcamera-v0.7.2/src/libcamera/pipeline/camss-vfe/hardware_focus.h').read_bytes()==(HERE/'hardware_focus.h').read_bytes()
else:shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[s for s in n if s=='pkg' or s.startswith('pkg-before') or s=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';header='src/libcamera/pipeline/camss-vfe/hardware_focus.h';pipeline='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
original={name:(old/'src/libcamera-v0.7.2'/name).read_text() for name in [header,pipeline]};text=original[header]
workspace='''struct LumaFocusWorkspace {
 static constexpr size_t kMaximumCells=320*240;
 unsigned width=0,height=0,columns=0,rows=0;
 std::array<unsigned,320> sampleX{},regionX{};
 std::vector<uint16_t> grid,smooth;
 bool prepare(unsigned w,unsigned h)
 {
  if(w<12 || h<12)return false;
  if(width==w && height==h)return true;
  const unsigned c=std::min(320U,w/2),r=std::min(240U,h/2);
  try {
   grid.reserve(kMaximumCells);smooth.reserve(kMaximumCells);
   grid.assign(size_t(c)*r,0);smooth.assign(size_t(c)*r,0);
  } catch(const std::bad_alloc &) {clear();return false;}
  for(unsigned x=0;x<c;++x){sampleX[x]=uint64_t(x)*(w-2)/(c-1);regionX[x]=x*FocusStatistics::kColumns/c;}
  width=w;height=h;columns=c;rows=r;return true;
 }
 void clear()
 {
  std::vector<uint16_t>().swap(grid);std::vector<uint16_t>().swap(smooth);
  width=height=columns=rows=0;
 }
 size_t storageBytes() const {return (grid.capacity()+smooth.capacity())*sizeof(uint16_t);}
};

'''
def replace(a,b):
 global text
 a=a.lstrip(' \t');b=b.lstrip(' \t')
 assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b)
replace('#include <optional>','#include <optional>\n#include <new>')
replace('inline FocusStatistics measureLumaFocus(',workspace+'inline FocusStatistics measureLumaFocus(')
replace('unsigned height,unsigned stride)\n{','unsigned height,unsigned stride,LumaFocusWorkspace *workspace=nullptr)\n{')
a=''' const unsigned columns=std::min(320U,width/2),rows=std::min(240U,height/2);
 std::array<unsigned,320> sampleX{},regionX{};
 for (unsigned x=0;x<columns;++x) {
  sampleX[x]=uint64_t(x)*(width-2)/(columns-1);
  regionX[x]=x*FocusStatistics::kColumns/columns;
 }
 std::vector<uint16_t> grid(size_t(columns)*rows),smooth(grid.size());'''
b=''' std::optional<LumaFocusWorkspace> local;
 if(!workspace){local.emplace();workspace=&*local;}
 if(!workspace->prepare(width,height))return result;
 const unsigned columns=workspace->columns,rows=workspace->rows;
 const auto &sampleX=workspace->sampleX,&regionX=workspace->regionX;
 auto &grid=workspace->grid,&smooth=workspace->smooth;
 /* Every grid cell and every smooth cell read below is overwritten this frame. */'''
replace(a,b)
replace('FocusMeasurementTiming *timing=nullptr)','FocusMeasurementTiming *timing=nullptr,LumaFocusWorkspace *workspace=nullptr)')
replace('configuration.size.width,configuration.size.height,configuration.stride);','configuration.size.width,configuration.size.height,configuration.stride,workspace);')
(tree/header).write_text(text);(HERE/'hardware_focus.h').write_text(text)
text=original[pipeline]
replace('std::vector<std::unique_ptr<FrameBuffer>> internalImages_;','std::vector<std::unique_ptr<FrameBuffer>> internalImages_;\n LumaFocusWorkspace focusWorkspace_;')
replace('  d->running_ = true;','''  
  if(d->lensActive_ && d->output_.width>=12 && d->output_.height>=12 &&
     !d->focusWorkspace_.prepare(d->output_.width,d->output_.height)){ret=-ENOMEM;goto error;}
  LOG(CamssVfe,Debug)<<"FOCUS_WORKSPACE_PREPARE epoch="<<d->epoch_<<" width="<<d->output_.width
   <<" height="<<d->output_.height<<" bytes="<<d->focusWorkspace_.storageBytes();
  d->running_ = true;''')
replace('d->internalImages_.clear();d->freeImages_={};d->internalRequests_.clear();','''d->focusWorkspace_.clear();
  LOG(CamssVfe,Debug)<<"FOCUS_WORKSPACE_STOP epoch="<<d->epoch_<<" bytes="<<d->focusWorkspace_.storageBytes();
  d->internalImages_.clear();d->freeImages_={};d->internalRequests_.clear();''')
replace('measureFrameFocus(buffer,focusConfig,&focusTiming);','measureFrameFocus(buffer,focusConfig,&focusTiming,&focusWorkspace_);')
(tree/pipeline).write_text(text)
(HERE/'0058-camss-bounded-focus-workspace.patch').write_text(''.join(''.join(difflib.unified_diff(original[n].splitlines(True),(tree/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n)) for n in [header,pipeline]))
state=json.loads((HERE.parent/'kernel445/source-state.json').read_text())
for row in state['source_hashes']:row['sha256']=hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()
state.update(stage=446,source=str(tree),baseline_stage=445,source_baseline_stage=445,changed_this_stage=[header,pipeline],build_pending=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=446,source=str(tree),changed_production_files=2,private_ipa_version=6,per_camera_workspace_prepared_before_stream_and_freed_at_stop=True,phone_changed=False,passed=True)))
