"""Preserve libcamera NV12's logical Y/UV layout while submitting one FULL plane."""
from pathlib import Path
import hashlib,json
import storage
HERE=Path(__file__).resolve().parent;tree=storage.candidate()/'src/libcamera-v0.7.2'
p=tree/'src/libcamera/pipeline/camss-vfe/camss_ipe.cpp';t=p.read_text()
a=t.index('if (bool(coarse) != pd10_');z=t.index('    if (params && !requestsEnabled_)',a)
t=t[:a]+'''if (bool(coarse) != pd10_ || (coarse && (coarse == input || coarse == output ||
        coarse->planes().size()!=1 || coarse->metadata().status!=FrameMetadata::FrameSuccess ||
        coarse->metadata().planes()[0].bytesused!=46080 ||
        coarse->_d()->kernelSequence()!=input->_d()->kernelSequence()))) return -EINVAL;
    auto planes = input->planes();
    std::vector<FrameBuffer::Plane> joined(planes.begin(),planes.end());
    if (coarse) {
        unsigned int used=0;for(const auto &p:input->metadata().planes())used+=p.bytesused;
        if(used!=460800 || (planes.size()!=1 && planes.size()!=2))return -EINVAL;
        if(planes.size()==1 && planes[0].length<460800)return -EINVAL;
        if(planes.size()==2 && (planes[0].fd.get()!=planes[1].fd.get() ||
            uint64_t(planes[0].offset)+307200!=planes[1].offset ||
            planes[0].length<307200 || planes[1].length<153600))return -EINVAL;
        joined={FrameBuffer::Plane{planes[0].fd,planes[0].offset,460800},coarse->planes()[0]};
    }
'''+t[z:]
a=t.index('    auto planes = input->planes();',t.index('    if (params && !requestsEnabled_)'));z=t.index('\tjob.request = request;',a)
t=t[:a]+'''    Job job{ input, coarse, std::make_unique<FrameBuffer>(joined) };
    /* Keep source FDs and original SOF through both queues and request DONE.
     * NV12's logical Y/UV views share one validated contiguous DMA interval. */
    auto &metadata=job.input->_d()->metadata();
    metadata.status=input->metadata().status;metadata.sequence=input->metadata().sequence;metadata.timestamp=input->metadata().timestamp;
    if(coarse) {metadata.planes()[0].bytesused=460800;metadata.planes()[1]=coarse->metadata().planes()[0];}
    else for(unsigned int i=0;i<planes.size();++i)metadata.planes()[i]=input->metadata().planes()[i];
'''+t[z:]
p.write_text(t)
s=json.loads((HERE/'source-state.json').read_text())
for r in s['source_hashes']:r['sha256']=hashlib.sha256((tree/r['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(s,indent=2)+'\n')
