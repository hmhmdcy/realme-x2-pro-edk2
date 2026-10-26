from pathlib import Path
import hashlib,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent
assert json.loads((HERE/'baseline-validation.json').read_text())['passed']
new=storage.candidate();old=new.parent/'libcamera435-gtm-history'
assert not new.exists()
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';pipeline=tree/'src/libcamera/pipeline/camss-vfe'
shutil.copyfile(HERE/'tone_trace.h',pipeline/'tone_trace.h')
path=pipeline/'camss_vfe.cpp';text=path.read_text()
def edit(a,b):
 global text
 assert text.count(a)==1,(a,text.count(a))
 text=text.replace(a,b)
edit('#include "camss_ipe.h"','#include "camss_ipe.h"\n#include "tone_trace.h"')
edit(' Request *ipeActive_ = nullptr;',' Request *ipeActive_ = nullptr;\n bool toneTraceSaved_ = false;')
needle=' if(d->sensorConfiguration_.pd10!=d->coarseEnabled_)'
assert text.count(needle)==1
text=text.replace(needle,' d->toneTraceSaved_=false;\n'+needle)
edit('  if(!ret)ret=ipe_->queue(buffer,output,tone.empty()?nullptr:&packet,requests_.at(request).coarse);','''  const char *traceDir=utils::secure_getenv("LIBCAMERA_CAMSS_VFE_TRACE_DIR");
  if(!ret && traceDir && *traceDir && !toneTraceSaved_ && sequence>=12 && toneFresh &&
     !tone.empty() && requests_.at(request).coarse) {
   toneTraceSaved_=true;
   std::string base=std::string(traceDir)+"/tone-"+std::to_string(sequence);
   ret=toneTraceBuffer(base+"-full.nv12",buffer,460800);
   if(!ret)ret=toneTraceBuffer(base+"-coarse.pd10",requests_.at(request).coarse,46080);
   if(!ret)ret=toneTraceBytes(base+"-params.bin",&packet,sizeof packet);
   LOG(CamssVfe,Info)<<"IPE_TONE_TRACE epoch="<<toneEpoch<<" sof="<<sequence<<" token="<<toneToken
    <<" revision="<<toneRevision<<" full-sequence="<<buffer->_d()->kernelSequence()
    <<" pd10-sequence="<<requests_.at(request).coarse->_d()->kernelSequence()<<" result="<<ret;
  }
  if(!ret)ret=ipe_->queue(buffer,output,tone.empty()?nullptr:&packet,requests_.at(request).coarse);''')
path.write_text(text)
state=json.loads((HERE.parent/'kernel435/source-state.json').read_text())
rels=[r['path'] for r in state['source_hashes']]+['src/libcamera/pipeline/camss-vfe/tone_trace.h']
state.update(stage=436,source_prepared=True,source=str(tree),private_ipa_version=5,
 source_hashes=[dict(path=r,sha256=hashlib.sha256((tree/r).read_bytes()).hexdigest()) for r in rels],
 changed_paths=['src/libcamera/pipeline/camss-vfe/camss_vfe.cpp','src/libcamera/pipeline/camss-vfe/tone_trace.h'])
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(stage=436,source_prepared=True,private_ipa_version=5,changed_paths=state['changed_paths'])))
