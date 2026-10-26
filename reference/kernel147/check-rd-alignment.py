from pathlib import Path
import gzip,struct,tarfile,json,hashlib
out=Path('/mnt/e/edk2-samurai-out/kernel147'); ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel147')
reports={}
for stage,label in [(146,'rd146'),(147,'aligned147')]:
    folder=out.parent / ('kernel'+str(stage))
    with tarfile.open(folder / (label+'-private.tar.gz')) as t:
        data={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
    for line in data['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1); assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
    records=[]; submits=0
    for name,raw in data.items():
        if not name.endswith('.rd.gz'): continue
        rd=gzip.decompress(raw); offset=0
        while offset<len(rd):
            typ,size=struct.unpack_from('<II',rd,offset); offset+=8
            assert offset+size<=len(rd)
            body=rd[offset:offset+size]; offset+=size
            if typ==3:
                lo,length=struct.unpack_from('<II',body)
                addr=lo | (struct.unpack_from('<I',body,8)[0]<<32 if size>8 else 0)
                records.append((addr,length))
            elif typ==6: submits+=1
    assert records and submits>0
    unaligned=sum(addr%65536!=0 for addr,length in records)
    assert (unaligned>0 if stage==146 else unaligned==0)
    reports[str(stage)]=dict(buffer_records=len(records),unique_buffers=len(set(records)),submits=submits,unaligned64k_buffer_records=unaligned)
    (folder / (label+'-rd-addresses-private.json')).write_text(json.dumps(records,indent=2)+'\n')
report=dict(before_after=reports,all_candidate_rd_bo_bases_aligned64k=True,baseline_contains_unaligned_bos=True,archive_members_sha256_verified=True)
(ref / 'rd-alignment-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K147_ACTUAL_RD_ALIGNMENT_CHANGE_VERIFIED')
