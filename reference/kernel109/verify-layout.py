from pathlib import Path
import hashlib,json,struct,tarfile,zlib
out=Path('/mnt/e/edk2-samurai-out/kernel109')
files={}
with tarfile.open(out/'layout-before.tar') as tar:
    for m in tar:
        if m.isfile(): files[m.name.split('/',1)[1]]=tar.extractfile(m).read()
for line in files['SHA256SUMS'].decode().splitlines():
    h,n=line.split('  ',1);assert hashlib.sha256(files[n.removeprefix('./')]).hexdigest()==h
p=json.loads((out/'preparation.json').read_text())
assert files['state.txt'].decode().splitlines()[0]==p['before_boot_id']
assert p['expected_full_boot_sha256'] in files['boot-logdump.sha256'].decode()
assert p['expected_logdump_sha256'] in files['boot-logdump.sha256'].decode()
assert all(l.endswith(b': OK') for l in files['nv-check.txt'].splitlines())
disks={}
for d in ['sda','sdb','sdc','sdd','sde','sdf']:
    geometry=files[d+'.geometry'].decode().splitlines();assert int(geometry[1])==4096
    blocks=int(geometry[0])//8
    def header(data,offset):
        h=data[offset:offset+4096];assert h[:8]==b'EFI PART'
        size,crc=struct.unpack_from('<II',h,12)
        check=bytearray(h[:size]);struct.pack_into('<I',check,16,0)
        assert zlib.crc32(check)&0xffffffff==crc
        return struct.unpack_from('<4Q',h,24),struct.unpack_from('<Q3I',h,72),h[56:72]
    primary,pt,guid=header(files[d+'.head'],4096)
    backup,bt,bguid=header(files[d+'.tail'],33*4096)
    assert primary[:2]==(1,blocks-1) and backup[:2]==(blocks-1,1) and guid==bguid
    lba,count,size,crc=pt
    table=files[d+'.head'][lba*4096:lba*4096+count*size]
    assert len(table)==count*size and zlib.crc32(table)&0xffffffff==crc
    blba,bcount,bsize,bcrc=bt
    start=(blba-(blocks-34))*4096
    btable=files[d+'.tail'][start:start+bcount*bsize]
    assert table==btable and crc==bcrc
    if d=='sda':
        matches=[]
        for i in range(count):
            entry=table[i*size:(i+1)*size]
            name=entry[56:128].decode('utf-16-le').rstrip('\0')
            if name=='userdata':
                a,b=struct.unpack_from('<QQ',entry,32);matches.append((a,b))
        assert len(matches)==1 and (matches[0][1]-matches[0][0]+1)*4096==p['userdata_bytes']
    disks[d]=dict(primary_crc_valid=True,backup_crc_valid=True,tables_equal=True,head_sha256=hashlib.sha256(files[d+'.head']).hexdigest(),tail_sha256=hashlib.sha256(files[d+'.tail']).hexdigest())
report=dict(stage=109,before_layout_valid=True,user_data_geometry_match=True,all_six_lun_gpt_crc_valid=True,boot_logdump_match_backups=True,nv_preserved_before=True,disks=disks)
(out/'layout-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('SIX_LUN_PRIMARY_BACKUP_GPT_CRC_AND_USERDATA_GEOMETRY_PASS')
