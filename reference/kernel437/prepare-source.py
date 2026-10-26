from pathlib import Path
import hashlib,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root=storage.mount.mounted_build().parent
new=root/'libcamera437-awb-history';old=root/'libcamera436-tone-domain';assert not new.exists()
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
T=new/'src/libcamera-v0.7.2';ipa=T/'src/ipa/camss-vfe';p=ipa/'camss.cpp';text=p.read_text()
def edit(a,b):
 global text
 assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b)
edit('#include "hardware_awb.h"','#include "hardware_awb.h"\n#include "awb_status.h"')
edit('\tstd::unique_ptr<HardwareAwb> awb_;','\tstd::unique_ptr<HardwareAwb> awb_;\n AppliedAwbStatus awbStatus_;')
text=text.replace('agc_.reset(); awb_.reset();','agc_.reset(); awb_.reset(); awbStatus_.reset();')
text=text.replace('if (awb_) awb_->reset();','if (awb_) awb_->reset();\n awbStatus_.reset();')
edit('\tawbEnabled_ = false; colourTemperature_.reset();','\tawbStatus_.reset();\n\tawbEnabled_ = false; colourTemperature_.reset();')
edit('\tif (result.status) { complete(); return; }','\tif (result.status) { awbStatus_.reset();if(awb_)awb_->reset();complete(); return; }')
edit('\tmetadata.set(controls::AwbLocked, false);\n double proposedRed=', ''' if(!result.parametersKnown || !result.rgbPresent || !context->second.awbEnabled) {
  awbStatus_.reset();if(awb_)awb_->reset();
 }
 double proposedRed=''')
edit('\t\tmetadata.set(controls::AwbLocked, awb.locked);', '''  awbStatus_.observe(sof,context->second.red,context->second.blue,awb.valid,awb.locked);''')
edit('\tLOG(IPACamss, Info) << "RGB epoch="', ''' const bool awbLocked=result.parametersKnown && result.rgbPresent && context->second.awbEnabled &&
  awbStatus_.locked(sof,context->second.red,context->second.blue);
 metadata.set(controls::AwbLocked,awbLocked);
 LOG(IPACamss,Info)<<"AWB_STATE epoch="<<epoch<<" sof="<<sof<<" revision="<<result.ispRevision
  <<" calculated="<<(result.awbRegions!=0)<<" regions="<<result.awbRegions<<" locked="<<awbLocked
  <<" red="<<(result.parametersKnown?context->second.red:0)<<" blue="<<(result.parametersKnown?context->second.blue:0);
\tLOG(IPACamss, Info) << "RGB epoch="''')
p.write_text(text);shutil.copyfile(HERE/'awb_status.h',ipa/'awb_status.h')
state=json.loads((HERE.parent/'kernel436/source-state.json').read_text());rels=[r['path'] for r in state['source_hashes']]+['src/ipa/camss-vfe/awb_status.h']
state.update(stage=437,source=str(T),source_prepared=True,changed_paths=['src/ipa/camss-vfe/camss.cpp','src/ipa/camss-vfe/awb_status.h'],source_hashes=[dict(path=r,sha256=hashlib.sha256((T/r).read_bytes()).hexdigest()) for r in rels])
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(dict(stage=437,source_prepared=True,private_ipa_version=5,awb_algorithm_thresholds_unchanged=True)))
