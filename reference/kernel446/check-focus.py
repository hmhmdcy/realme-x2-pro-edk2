"""Check exact results across poisoned cached grids, layout changes and release."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
contract=(HERE.parent/'kernel445/focus-contract.cpp').read_text().replace('using namespace libcamera;','using namespace libcamera;\nstatic LumaFocusWorkspace workspace;')
a=' auto a=referenceLumaFocus(data,bytes,w,h,stride),b=measureLumaFocus(data,bytes,w,h,stride);'
b=''' const bool valid=data&&w>=12&&h>=12&&stride>=w&&uint64_t(h-1)*stride+w<=bytes;
 if(valid){assert(workspace.prepare(w,h));std::fill(workspace.grid.begin(),workspace.grid.end(),0xa55a);std::fill(workspace.smooth.begin(),workspace.smooth.end(),0x5aa5);}
 const auto *grid=workspace.grid.data(),*smooth=workspace.smooth.data();const auto storage=workspace.storageBytes();
 const unsigned previousWidth=workspace.width,previousHeight=workspace.height;
 auto a=referenceLumaFocus(data,bytes,w,h,stride),b=measureLumaFocus(data,bytes,w,h,stride,&workspace);
 assert(workspace.grid.data()==grid&&workspace.smooth.data()==smooth&&workspace.storageBytes()==storage);
 if(!valid)assert(workspace.width==previousWidth&&workspace.height==previousHeight);'''
assert contract.count(a)==1;contract=contract.replace(a,b)
contract=contract.replace('measureLumaFocus(data.data(),data.size(),w,h,stride):','measureLumaFocus(data.data(),data.size(),w,h,stride,&workspace):')
marker='  std::cout<<"{\\"synthetic_passed'
extra='''  assert(!workspace.prepare(11,12));workspace.clear();assert(!workspace.storageBytes()&&!workspace.width&&!workspace.height);
  assert(workspace.prepare(1280,720));assert(workspace.storageBytes()==307200);
  std::vector<uint8_t> sequence(1280*720,121);
  const auto *stableGrid=workspace.grid.data(),*stableSmooth=workspace.smooth.data();
  for(unsigned i=0;i<16;++i){sequence[i*1000]=uint8_t(i*13);assert(compare(sequence.data(),sequence.size(),1280,720,1280).valid);assert(workspace.grid.data()==stableGrid&&workspace.smooth.data()==stableSmooth);}
  auto plain=measureLumaFocus(sequence.data(),sequence.size(),1280,720,1280);
  assert(plain.figureOfMerit()==referenceLumaFocus(sequence.data(),sequence.size(),1280,720,1280).figureOfMerit());
  workspace.clear();assert(workspace.grid.empty()&&workspace.smooth.empty()&&!workspace.storageBytes());
'''
assert contract.count(marker)==1;contract=contract.replace(marker,extra+marker)
(HERE/'focus-contract.cpp').write_text(contract)
source=(HERE.parent/'kernel445/check-focus.py').read_text().replace('stage=445','stage=446').replace("old=volume/'libcamera444-focused-ipe/src/libcamera-v0.7.2'", "old=volume/'libcamera445-focus-grid/src/libcamera-v0.7.2'").replace('camss445-focus','camss446-focus')
source=source.replace("optimized=function((tree/name).read_text())", "header=(tree/name).read_text();workspace=header[header.index('struct LumaFocusWorkspace {'):header.index('inline FocusStatistics measureLumaFocus(')];optimized=workspace+function(header)")
source=source.replace('#include <optional>\\n','#include <optional>\\n#include <new>\\n')
exec(compile(source,str(HERE/'check-focus.py'),'exec'))
p=HERE/'focus-validation.json';d=json.loads(p.read_text());d.update(poisoned_workspace_and_geometry_changes_preserve_exact_statistics=True,steady_grid_addresses_and_capacity_unchanged=True,explicit_release_reprepare_and_legacy_fallback_checked=True,persistent_sequence_cases=16,maximum_tested_grid_storage_bytes=307200)
p.write_text(json.dumps(d,indent=2)+'\n')
