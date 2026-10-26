#!/usr/bin/env python3
"""Validate and reconstruct an Android sparse image into a local sparse file."""
import errno, hashlib, json, os, struct, runpy
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel126/ensure-build-volume.py')
from pathlib import Path

stage=Path('/home/cy122/pmos-samurai-build126')
out=Path('/mnt/e/edk2-samurai-out/kernel128')
sparse=out/'samurai-rootfs-f2fs-k128-device-fixed.simg'
source=stage/'samurai-rootfs-f2fs-k128-device-fixed.raw.img'
restored=stage/'samurai-rootfs-f2fs-k128-device-fixed-restored.raw.img'
assert not restored.exists()
expected_size=119033245696
stats={'raw_chunks':0,'fill_chunks':0,'skip_chunks':0,'crc_chunks':0}
with sparse.open('rb') as f, source.open('rb') as original, restored.open('xb') as target:
    magic,major,minor,file_h,chunk_h,block_size,blocks,chunks,checksum=struct.unpack('<I4H4I',f.read(28))
    assert magic==0xed26ff3a and major==1 and block_size==4096
    assert file_h>=28 and chunk_h>=12 and blocks*block_size==expected_size
    f.seek(file_h)
    block_offset=0
    for index in range(chunks):
        kind,reserved,nblocks,total_size=struct.unpack('<2H2I',f.read(12))
        assert total_size>=chunk_h
        f.seek(chunk_h-12,1)
        size=nblocks*block_size
        offset=block_offset*block_size
        assert offset+size<=expected_size
        original.seek(offset)
        target.seek(offset)
        if kind==0xcac1:
            stats['raw_chunks']+=1
            assert total_size==chunk_h+size
            remain=size
            while remain:
                data=f.read(min(remain,4*1024*1024))
                assert data and data==original.read(len(data))
                target.write(data)
                remain-=len(data)
        elif kind==0xcac2:
            stats['fill_chunks']+=1
            assert total_size==chunk_h+4
            pattern=f.read(4)
            remain=size
            while remain:
                step=min(remain,4*1024*1024)
                data=pattern*(step//4)
                assert data==original.read(step)
                if pattern!=b'\0'*4:
                    target.write(data)
                else:
                    target.seek(step,1)
                remain-=step
        elif kind==0xcac3:
            stats['skip_chunks']+=1
            assert total_size==chunk_h
            try:
                next_data=os.lseek(original.fileno(),offset,os.SEEK_DATA)
            except OSError as error:
                assert error.errno==errno.ENXIO
                next_data=expected_size
            assert next_data>=offset+size, 'Skipped chunk intersects source data'
            target.seek(size,1)
        elif kind==0xcac4:
            stats['crc_chunks']+=1
            assert nblocks==0 and total_size==chunk_h+4
            f.read(4)
        else:
            raise ValueError(f'Unknown sparse chunk {kind:#x}')
        block_offset+=nblocks
    assert block_offset==blocks and not f.read(1)
    target.truncate(expected_size)
    target.flush()
    os.fsync(target.fileno())

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(4*1024*1024),b''):
            h.update(data)
    return h.hexdigest()

audit={
    'android_sparse_magic':hex(magic),'version':f'{major}.{minor}',
    'block_size':block_size,'expanded_bytes':blocks*block_size,
    'expanded_gib':round(blocks*block_size/1024**3,4),
    'sparse_bytes':sparse.stat().st_size,'chunks':chunks,**stats,
    'sha256':digest(sparse),'payload_matches_raw_source':True,
    'skipped_ranges_verified_as_source_holes':True,
    'reconstructed_wsl_path':str(restored),
}
(out/'sparse-fixed-validation.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps(audit,indent=2))
