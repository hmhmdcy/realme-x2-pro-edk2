from pathlib import Path
import hashlib,tarfile,urllib.request,json
private=Path('/mnt/e/edk2-samurai-out/kernel211');archive=private/'libcamera-v0.7.2.tar.gz'
expected='b317cdc96f61682ee0bf26dfb7c4d6441db9a9c5b93ab53528121a8cd44862b3d59cbaa3881bb0837e3e381564c184c7b742124aef4267eea754c6083de353c1'
if not archive.exists():
    with urllib.request.urlopen('https://gitlab.freedesktop.org/camera/libcamera/-/archive/v0.7.2/libcamera-v0.7.2.tar.gz',timeout=60) as response:data=response.read(20*1024*1024)
    assert hashlib.sha512(data).hexdigest()==expected
    archive.write_bytes(data)
assert hashlib.sha512(archive.read_bytes()).hexdigest()==expected
targets=['src/libcamera/software_isp/software_isp.cpp','src/ipa/simple/soft_simple.cpp','src/ipa/libipa/camera_sensor_helper.cpp','src/libcamera/dma_buf_allocator.cpp']
out=private/'libcamera-source';out.mkdir(exist_ok=True)
with tarfile.open(archive) as t:
    for name in targets:
        matches=[m for m in t.getmembers() if m.name.endswith('/'+name) and m.isfile()];assert len(matches)==1
        data=t.extractfile(matches[0]).read();path=out/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        lines=data.decode().splitlines()
        terms={'software_isp.cpp':['softISPMode','dmaHeap_','outputAllocator_'],'soft_simple.cpp':['gain_','gainCode','sensorHelper_','gain('],'camera_sensor_helper.cpp':['CameraSensorHelperImx','gainConstants_ =','gainType_ ='],'dma_buf_allocator.cpp':['providerInfos','/dev/dma_heap']}.get(Path(name).name,[])
        selected=set()
        for i,line in enumerate(lines):
            if any(term in line for term in terms):selected.update(range(max(0,i-2),min(len(lines),i+5)))
        print(json.dumps({'source':name,'lines':{i+1:lines[i] for i in sorted(selected)}}))
