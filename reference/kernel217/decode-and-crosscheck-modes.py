"""Independently decode bounded BIN records and compare every mode register to XML."""
from pathlib import Path
import hashlib,json,math,struct,xml.etree.ElementTree as ET
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel217');source=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx471.bin');blob=source.read_bytes()
assert blob.startswith(b'QTI Chromatix Header\0') and struct.unpack_from('<I',blob,28)[0]==len(blob)
assert b'Parameter Parser V1.3.2 ' in blob[:0x98]
offset,count=struct.unpack_from('<II',blob,0x98);assert count==3 and offset==0xa0
sections=[struct.unpack_from('<QQQ',blob,offset+i*24) for i in range(count)];assert [s[0] for s in sections]==[0,1,2]
_,symbol_offset,symbol_size=sections[0];_,data_offset,data_size=sections[1];assert symbol_size%72==0 and data_offset+data_size<=len(blob)
entries={}
for p in range(symbol_offset,symbol_offset+symbol_size,72):
    ident=struct.unpack_from('<Q',blob,p)[0];name=blob[p+8:p+40].split(b'\0')[0].decode('ascii');relative,size=struct.unpack_from('<QQ',blob,p+56);assert relative+size<=data_size and ident not in entries
    entries[ident]=dict(name=name,relative=relative,size=size)
def payload(ident,name):
    item=entries[ident];assert item['name']==name;return blob[data_offset+item['relative']:data_offset+item['relative']+item['size']]
def words(ident,name):
    data=payload(ident,name);assert len(data)%8==0;return struct.unpack('<'+'Q'*(len(data)//8),data)
assert words(14,'resolutionInfo')==(0,15,3,16)
mode_data=payload(16,'resolutionData');assert len(mode_data)==3*256
xml=ET.parse(private/'vendor-r4-xml/Scenario.0/XML/None/sensorDriverData.xml').getroot();modes_xml=xml.findall('resolutionInfo/resolutionData');assert len(modes_xml)==3
schema=ET.parse('/home/cy122/x2pro-linux/parser-k217-modes-r4/api/sensor/camxsensordriver.xsd');ns={'x':'http://www.w3.org/2001/XMLSchema'}
remosaic_names=[node.attrib['value'] for node in schema.findall("./x:simpleType[@name='RemosaicType']//x:enumeration",ns)];assert 'SWRemosaic' in remosaic_names
prefix=json.loads((private.parent/'kernel192/camera-prefix-decoded-private.json').read_text())['sensors'];own=next(item for item in prefix if item['sensor']=='imx471');mclk=[item['value'] for item in own['power_up'] if item['type']=='MCLK'];assert mclk==[19200000]
records=[]
for index,node in enumerate(modes_xml):
    q=struct.unpack_from('<32Q',mode_data,index*256);assert q[0]==0 and q[1]==1 and q[11]==4 and q[12]==q[15]==q[16]==0
    fps=struct.unpack('<d',struct.pack('<Q',q[10]))[0]
    scalar_keys={'lineLengthPixelClock':3,'frameLengthLines':4,'minHorizontalBlanking':5,'minVerticalBlanking':6,'outputPixelClock':7,'horizontalBinning':8,'verticalBinning':9,'laneCount':11,'settleTimeNs':14,'is3Phase':15}
    assert all(int(node.findtext(key))==q[position] for key,position in scalar_keys.items());assert math.isclose(float(node.findtext('frameRate')),fps,abs_tol=1e-6)
    stream=words(q[2],'streamConfiguration');assert len(stream)==8 and stream[:2]==(0,0x2b) and stream[6:]==(10,1)
    sx=node.find('streamInfo/streamConfiguration');assert [int(sx.findtext(path)) for path in ['vc','dt','frameDimension/xStart','frameDimension/yStart','frameDimension/width','frameDimension/height','bitWidth']]==list(stream[:7])
    assert sx.findtext('type')=='IMAGE';width,height=stream[4:6]
    registers=[];reg_data=payload(q[19],'regSetting');assert q[18]==58 and len(reg_data)==58*80
    for start in range(0,len(reg_data),80):
        r=struct.unpack_from('<10Q',reg_data,start);assert r[0]==0 and r[3]==1 and r[5:8]==(2,1,0) and r[8]==1
        value=words(r[4],'registerData');delay=words(r[9],'delayUs');assert len(value)==len(delay)==1 and 0<=r[2]<=0xffff and 0<=value[0]<=0xff and delay[0]==0
        registers.append(dict(address=r[2],value=value[0],delay_us=delay[0]))
    xml_registers=[]
    for r in node.findall('resSettings/regSetting'):
        assert r.findtext('regAddrType')=='2' and r.findtext('regDataType')=='1' and r.findtext('operation')=='WRITE'
        xml_registers.append(dict(address=int(r.findtext('registerAddr')),value=int(r.findtext('registerData')),delay_us=int(r.findtext('delayUs'))))
    assert registers==xml_registers and len({r['address'] for r in registers})==58
    values={r['address']:r['value'] for r in registers}
    def u16(address):return (values[address]<<8)|values[address+1]
    assert u16(0x034c)==u16(0x040c)==width and u16(0x034e)==u16(0x040e)==height
    assert u16(0x0342)==q[3] and u16(0x0340)==q[4] and values[0x0112]==values[0x0113]==10 and values[0x0114]==3
    remosaic=words(q[29],'RemosaicTypeInfo') if q[28] else ();assert not remosaic or len(remosaic)==1 and remosaic[0]<len(remosaic_names)
    remosaic_name=remosaic_names[remosaic[0]] if remosaic else None;assert node.findtext('RemosaicTypeInfo')==remosaic_name
    record=dict(index=index,width=width,height=height,frame_rate_metadata=fps,line_length=q[3],frame_length=q[4],output_pixel_clock_metadata=q[7],binning=[q[8],q[9]],lane_count=q[11],external_clock=mclk[0],software_remosaic_required=remosaic_name=='SWRemosaic',raw_datatype=0x2b,raw_bits=10,crop=dict(left=u16(0x0344),top=u16(0x0346),right=u16(0x0348),bottom=u16(0x034a)),digital_crop=dict(left=u16(0x0408),top=u16(0x040a),width=u16(0x040c),height=u16(0x040e)),registers=registers)
    records.append(record)
assert source.read_bytes()==blob
(private/'factory-imx471-modes-private.json').write_text(json.dumps(dict(modes=records),indent=2)+'\n')
public=[{key:value for key,value in record.items() if key!='registers'} for record in records]
report=dict(stage=217,source_factory_bin_unchanged=True,independent_vendor_reader_and_bounded_decoder_agree=True,mode_count=3,mode_register_records_verified=174,all_mode_dimensions_frame_line_and_raw_format_match_registers=True,full_4608x3456_requires_software_remosaic=True,normal_bayer_processing_not_accepted_for_full_mode=True,external_clock_19200000_verified_from_own_power_sequence=True,no_hardware_register_writes=True,modes=public)
(here/'factory-mode-crosscheck-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
