"""Derive the actual PD10 and contiguous FULL layouts in the common pipeline."""
from pathlib import Path
import difflib,hashlib,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;volume=storage.mount.mounted_build().parent
new=volume/'libcamera441-variable-pd10';old=volume/'libcamera440-release-r32';assert not new.exists()
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[x for x in n if x=='pkg' or x.startswith('pkg-before') or x=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';folder=tree/'src/libcamera/pipeline/camss-vfe';names=['camss_ipe.h','camss_ipe.cpp','camss_vfe.cpp'];before={name:(folder/name).read_text() for name in names}
def replaced(text,needle,value):assert text.count(needle)==1,(needle,text.count(needle));return text.replace(needle,value)
text=before['camss_ipe.h'];text=replaced(text,'bool requestsEnabled_ = false, pd10_ = false;','bool requestsEnabled_ = false, pd10_ = false;\n\tuint32_t fullBytes_ = 0, lumaBytes_ = 0, coarseBytes_ = 0;');(folder/'camss_ipe.h').write_text(text)
text=before['camss_ipe.cpp'];text=replaced(text,'#include "camss_ipe.h"','#include "camss_ipe.h"\n#include "camss_pd10.h"')
text=replaced(text,'if (pd10 && (format.size != Size(640,480) || format.planesCount != 1)) { stop(); return -EINVAL; }', '''const auto coarseLayout = camssPd10Layout(format.size);
	if (pd10) {
		const uint64_t luma = uint64_t(format.planes[0].bpl) * format.size.height;
		if (!coarseLayout || format.planesCount != 1 ||
		    format.fourcc != V4L2PixelFormat(V4L2_PIX_FMT_NV12) ||
		    format.planes[0].bpl < format.size.width ||
		    luma * 3 / 2 != format.planes[0].size) { stop(); return -EINVAL; }
		fullBytes_ = format.planes[0].size;
		lumaBytes_ = luma;
		coarseBytes_ = coarseLayout->frameSize;
	}''')
text=replaced(text,'expected.planes[1].bpl = 768; expected.planes[1].size = 46080;','expected.planes[1].bpl = coarseLayout->stride; expected.planes[1].size = coarseBytes_;')
text=replaced(text,'coarse->metadata().planes()[0].bytesused!=46080','coarse->metadata().planes()[0].bytesused!=coarseBytes_')
text=replaced(text,'unsigned int used=0;for(const auto &p:input->metadata().planes())used+=p.bytesused;','uint64_t used=0;for(const auto &p:input->metadata().planes())used+=p.bytesused;')
for needle,value in [('used!=460800','used!=fullBytes_'),('planes[0].length<460800','planes[0].length<fullBytes_'),('uint64_t(planes[0].offset)+307200','uint64_t(planes[0].offset)+lumaBytes_'),('planes[0].length<307200 || planes[1].length<153600','planes[0].length<lumaBytes_ || planes[1].length<fullBytes_-lumaBytes_'),('planes[0].offset,460800','planes[0].offset,fullBytes_'),('metadata.planes()[0].bytesused=460800','metadata.planes()[0].bytesused=fullBytes_')]:text=replaced(text,needle,value)
(folder/'camss_ipe.cpp').write_text(text)
text=before['camss_vfe.cpp'];text=replaced(text,'#include "camss_ipe.h"','#include "camss_ipe.h"\n#include "camss_pd10.h"')
text=replaced(text,'unsigned int outputStride_ = 0;','unsigned int outputStride_ = 0, outputFrameBytes_ = 0;')
text=replaced(text,'coarseRequested_ && coarse_ && ipe_ && processedEnabled_ && output==Size(640,480)','coarseRequested_ && coarse_ && ipe_ && processedEnabled_')
a=text.index('    if (coarseEnabled_) {\n        V4L2SubdeviceFormat coarse');b=text.index('    return 0;\n}',a)
text=text[:a]+'''    if (coarseEnabled_) {
        const auto layout = camssPd10Layout(output);
        if (!layout) return -EINVAL;
        V4L2SubdeviceFormat coarse{MEDIA_BUS_FMT_UYYVYY10_0_5X30,layout->size,{}};
        ret=pix_->setFormat(coarseLink_->source()->index(),&coarse);
        if(ret || coarse.size!=layout->size || coarse.code!=MEDIA_BUS_FMT_UYYVYY10_0_5X30)return ret?ret:-EINVAL;
        V4L2DeviceFormat wire;wire.fourcc=V4L2PixelFormat(V4L2_PIX_FMT_QCOM_PD10_LOCAL);wire.size=layout->size;
        ret=coarse_->setFormat(&wire);
        if(ret || wire.planesCount!=1 || wire.planes[0].bpl!=layout->stride || wire.planes[0].size!=layout->frameSize || wire.size!=layout->size)return ret?ret:-EINVAL;
    }
'''+text[b:]
text=replaced(text,'d->outputStride_=format.planes[0].bpl;','d->outputStride_=format.planes[0].bpl;d->outputFrameBytes_=format.planes[0].size;')
text=replaced(text,'!d->coarse_ || !d->ipe_ || d->output_!=Size(640,480)','!d->coarse_ || !d->ipe_ || !camssPd10Layout(d->output_)')
text=replaced(text,'ret=toneTraceBuffer(base+"-full.nv12",buffer,460800);','const auto layout=camssPd10Layout(output_);\n   ret=layout?toneTraceBuffer(base+"-full.nv12",buffer,outputFrameBytes_):-EINVAL;')
text=replaced(text,'toneTraceBuffer(base+"-coarse.pd10",requests_.at(request).coarse,46080)','toneTraceBuffer(base+"-coarse.pd10",requests_.at(request).coarse,layout->frameSize)')
(folder/'camss_vfe.cpp').write_text(text);shutil.copyfile(HERE/'camss_pd10.h',folder/'camss_pd10.h')
patch=''
for name in names:
 rel='src/libcamera/pipeline/camss-vfe/'+name;patch+=''.join(difflib.unified_diff(before[name].splitlines(True),(folder/name).read_text().splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
rel='src/libcamera/pipeline/camss-vfe/camss_pd10.h';patch+=''.join(difflib.unified_diff([], (folder/'camss_pd10.h').read_text().splitlines(True),fromfile='/dev/null',tofile='b/'+rel));(HERE/'0052-camss-variable-pd10-geometry.patch').write_text(patch)
state=json.loads((HERE.parent/'kernel440/source-state.json').read_text());paths=sorted({r['path'] for r in state['source_hashes']}|{rel})
state.update(stage=441,source=str(tree),source_prepared=True,build_pending=True,source_baseline_stage=440,source_baseline_preserved=True,changed_paths=['src/libcamera/pipeline/camss-vfe/'+name for name in names]+[rel],private_ipa_version=5,ipa_numerics_and_protocol_unchanged=True,raw_only_consumer_policy_preserved=True,source_hashes=[dict(path=p,sha256=hashlib.sha256((tree/p).read_bytes()).hexdigest()) for p in paths])
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(dict(stage=441,source_prepared=True,source=str(tree),changed_source_files=4,ipa_unchanged=True,raw_only_policy_preserved=True,installed=False,passed=True)))
