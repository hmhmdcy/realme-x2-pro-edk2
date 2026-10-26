"""Audit original WB/LSC type-table regions without trusting the mismatched full XML."""
from pathlib import Path
import hashlib,json,struct,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent
P=host.PRIVATE
original=P.parent/'kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx319.bin'
raw=original.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='e2d68359e85af97dbc686d63ca140ae2af87542023245c7307a57d3aeba21704'
table,count=struct.unpack_from('<II',raw,0x98)
sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
_,start,length=sections[0];base,size=sections[1][1:]
entries={}
for pos in range(start,start+length,72):
    uid=struct.unpack_from('<Q',raw,pos)[0]
    name=raw[pos+8:pos+40].split(b'\0')[0].decode()
    offset,nbytes=struct.unpack_from('<QQ',raw,pos+56)
    assert offset+nbytes<=size
    entries[uid]=(name,offset,nbytes)
def words(uid):
    name,offset,nbytes=entries[uid];assert nbytes%8==0
    return struct.unpack_from('<'+'Q'*(nbytes//8),raw,base+offset)
root=words(5);assert entries[5][0]=='EEPROMDriverData' and len(root)==203
# Classify the original arrays by their schema-defined strides, not a guessed root offset.
types={}
for uid,(name,offset,nbytes) in entries.items():
    positions=[i for i,v in enumerate(root) if v==uid]
    if name=='lightInfo' and len(positions)==1:
        position=positions[0];n=root[position-1]
        if n==5 and nbytes==n*15*8:types['WB']=(uid,position,n)
        if n==5 and nbytes==n*17*8:types['LSC']=(uid,position,n)
assert set(types)=={'WB','LSC'}
wuid,wpos,n=types['WB'];luid,lpos,ln=types['LSC']
wstart=wpos-4;lstart=lpos-3
assert root[wstart:wstart+3]==(1,1,0) # available, LITTLE, INDIVIDUAL
assert root[lstart:lstart+2]==(1,1)
qvalue=struct.unpack('<f',struct.pack('<I',root[wpos+5]))[0]
assert qvalue==1 and root[wpos+6]==0
mesh=root[lpos+1];increments=root[lpos+2:lpos+6]
assert mesh==221 and increments==(5,5,5,5)
wb=[list(words(wuid)[i*15:(i+1)*15]) for i in range(n)]
lsc=[list(words(luid)[i*17:(i+1)*17]) for i in range(ln)]
for row in wb:
    assert row[0] in range(5)
    assert all(row[i+1]==65535 for i in [1,3,5,7])
    assert all(row[i]==0 for i in range(9,15))
for row in lsc:
    assert row[0] in range(5)
    assert row[1:]==[212,192,208,255,212,48,209,255,212,12,210,255,212,3,211,255]
layout=dict(source='original module type-table arrays',wb_root_start_word=wstart,lsc_root_start_word=lstart,
            wb_available=True,wb_little_endian=True,wb_individual=True,q_value=qvalue,
            wb_lights=wb,lsc_lights=lsc,mesh_points=mesh,increments=list(increments),
            root_schema_not_fully_reconstructed=True,factory_checksum_verified=False,apply_allowed=False)
(P/'original-wb-lsc-layout-private.json').write_text(json.dumps(layout,indent=2)+'\n')
sample1=(P.parent/'kernel299/imx319-eeprom-read1-private.bin').read_bytes()
sample2=(P.parent/'kernel299/imx319-eeprom-read2-private.bin').read_bytes()
assert len(sample1)==12287 and sample1==sample2
def integer(offset,mask):
    assert mask in [0,65535]
    return int.from_bytes(sample1[offset:offset+2],'little') if mask else 0
def byte(offset,mask):
    assert 0<=offset<len(sample1) and 0<mask<=255
    low=(mask&-mask).bit_length()-1
    return (sample1[offset]&mask)>>low
unitwb=[]
for row in wb:
    r,gr,b,gb=[integer(row[i],row[i+1]) for i in [1,3,5,7]]
    unitwb.append(dict(illuminant=row[0],r=r,gr=gr,b=b,gb=gb,denominator_valid=gb!=0,
                       ratios=[r/gb,b/gb,gr/gb] if gb else None))
unitlsc=[]
for row in lsc:
    channels=[]
    for channel in range(4):
        msb,msbmask,lsb,lsbmask=row[1+channel*4:5+channel*4]
        channelValues=[(byte(msb+i*increments[channel],msbmask)<<8)|byte(lsb+i*increments[channel],lsbmask) for i in range(mesh)]
        channels.append(channelValues)
    unitlsc.append(dict(illuminant=row[0],channels=channels))
(P/'unit-wb-lsc-private.json').write_text(json.dumps(dict(wb=unitwb,lsc=unitlsc,checksum_verified=False,apply_allowed=False),indent=2)+'\n')
decoded=ET.parse(P.parent/'kernel299/imx319-eeprom-layout-private.xml')
oldmesh=int(decoded.findtext('./formatInfo/LSC/meshHWRollOffSize'))
oldq=float(decoded.findtext('./formatInfo/WB/qValue'))
assert oldmesh!=mesh and oldq!=qvalue
report=dict(stage=304,original_module_source_sha256=hashlib.sha256(raw).hexdigest(),
            full_xml_schema_alignment_failed=True,previous_xml_q_value=oldq,original_q_value=qvalue,
            previous_xml_mesh_points=oldmesh,original_mesh_points=mesh,
            original_type_arrays_wb_stride_words=15,original_type_arrays_lsc_stride_words=17,
            wb_illuminants=n,lsc_illuminants=ln,lsc_channels=4,lsc_mesh_dimensions_candidate=[17,13],lsc_geometry_verified=False,
            lsc_samples_decoded=mesh*4*ln,wb_denominators_valid=sum(x['denominator_valid'] for x in unitwb),
            duplicate_unit_reads_equal=True,unit_values_and_hashes_kept_private=True,
            factory_checksum_verified=False,complete_layout_verified=False,
            no_phone_operations=True,no_individual_calibration_applied=True)
(HERE/'eeprom-layout-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
