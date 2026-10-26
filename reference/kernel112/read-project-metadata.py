"""Read only the stock project/SOC SMEM records from the verified SMEM RAM.

Layouts follow Linux drivers/soc/qcom/smem.c and Realme's
include/soc/oppo/oppo_project.h. No MMIO or memory writes are performed.
"""
from pathlib import Path
import hashlib, json, os, struct

assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==Path(
    '/var/lib/samurai/k112-first-before-slpi/boot-id-private.txt').read_text().strip()
assert Path('/sys/class/remoteproc/remoteproc0/name').read_text().strip()=='slpi'
assert Path('/sys/class/remoteproc/remoteproc0/state').read_text().strip()=='offline'
reg=Path('/sys/firmware/devicetree/base/reserved-memory/memory@86000000/reg').read_bytes()
assert struct.unpack('>QQ',reg)==(0x86000000,0x200000)
base,size=struct.unpack('>QQ',reg)
dest=Path('/run/k112-project-metadata'); assert not dest.exists()
def read(offset,length):
    assert 0<=offset and 0<length<=4096 and offset+length<=size
    data=os.pread(fd,length,base+offset)
    assert len(data)==length
    return data
fd=os.open('/dev/mem',os.O_RDONLY|os.O_SYNC)
try:
    table=read(size-4096,4096)
    assert table[:4]==b'$TOC'
    version,count=struct.unpack_from('<II',table,4)
    assert version==1 and 0<count<=64 and 32+count*48<=4096
    global_part=None
    for i in range(count):
        offset,length,flags,h0,h1,cacheline=struct.unpack_from('<IIIHHI',table,32+i*48)
        if h0==h1==0xfffe:
            assert global_part is None
            global_part=(offset,length,cacheline)
    items={}
    if global_part:
        part,length,cacheline=global_part
        assert part+length<=size-4096 and cacheline>0 and cacheline&(cacheline-1)==0
        header=read(part,32)
        magic,h0,h1,actual,free_uncached,free_cached=struct.unpack_from('<4sHHIII',header)
        assert magic==b'$PRT' and h0==h1==0xfffe and actual==length
        assert 32<=free_uncached<=free_cached<=length
        pos=32; entries=0
        while pos<free_uncached:
            canary,item,n,pad,hpad,res=struct.unpack('<HHIHHI',read(part+pos,16))
            assert canary==0xa5a5 and hpad==0 and pad<=n and pos+16+n<=free_uncached
            if item in [135,137]:
                assert item not in items and 0<n-pad<=4096
                items[item]=read(part+pos+16,n-pad)
            pos+=16+n; entries+=1
            assert entries<=2048
        assert pos==free_uncached
    else:
        for item in [135,137]:
            allocated,offset,length,aux=struct.unpack('<IIII',read(208+item*16,16))
            assert allocated and aux&0xfffffffc==0 and 0<length<=4096
            items[item]=read(offset,length)
    assert set(items)=={135,137}, 'Project/SOC records absent; do not guess a board profile'
    fmt,soc_id,soc_version=struct.unpack_from('<III',items[137])
    assert soc_id==339 and soc_version==0x20002
    raw=items[135]; assert len(raw)>=13
    project=struct.unpack_from('<I',raw)[0]
    assert project==19781, 'Unexpected stock project identity'
    report=dict(project=project,modem_type=raw[4],operator=raw[5],pcb_version=raw[6],
        boot_mode=raw[7],machine_type=raw[8],soc_id=soc_id,soc_revision='2.2',
        raw_project_sha256=hashlib.sha256(raw).hexdigest(),memory_read_only=True)
    dest.mkdir(mode=0o700)
    (dest/'project-private.json').write_text(json.dumps(report,indent=2)+'\n')
    (dest/'project-record-private.bin').write_bytes(raw)
    (dest/'modemType').write_text(str(raw[4]))
    print('VERIFIED_STOCK_PROJECT_METADATA_READ_ONLY; BOARD_AND_MODEM_PROPERTY_RECOVERED')
finally:
    os.close(fd)
