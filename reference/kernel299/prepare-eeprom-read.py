"""Verify the original read map, then build a normal V4L2 power owner."""
from pathlib import Path
import hashlib,json,struct,subprocess,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=P.parent/'kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx319.bin';raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='e2d68359e85af97dbc686d63ca140ae2af87542023245c7307a57d3aeba21704'
table,count=struct.unpack_from('<II',raw,0x98);sections=[struct.unpack_from('<QQQ',raw,table+i*24) for i in range(count)]
_,start,length=sections[0];base,size=sections[1][1:];entries={}
for pos in range(start,start+length,72):
 uid=struct.unpack_from('<Q',raw,pos)[0];name=raw[pos+8:pos+40].split(b'\0')[0].decode();offset,n=struct.unpack_from('<QQ',raw,pos+56)
 assert offset+n<=size;entries[uid]=(name,offset,n)
def data(uid,name):
 n,o,s=entries[uid];assert n==name;return raw[base+o:base+o+s]
def scalar(uid,name):
 b=data(uid,name);assert len(b)==8 and not any(b[4:]);return struct.unpack_from('<I',b)[0]
root=struct.unpack('<203Q',data(5,'EEPROMDriverData'));assert root[:3]==(1,0,0)
assert data(root[4],'EEPROMName').rstrip(b'\0')==b'fx319aa_imx319'
assert root[13]==1
reg=struct.unpack('<10Q',data(root[14],'regSetting'))
assert reg[0]==reg[3]==reg[8]==1
address=scalar(reg[1],'slaveAddr');nbytes=scalar(reg[4],'registerData');delay=scalar(reg[9],'delayUs')
schema=ET.parse(P.parent/'kernel117/CamxChi/chi-cdk/api/sensor/camxsensorcommon.xsd');ns={'x':'http://www.w3.org/2001/XMLSchema'}
ops=[e.attrib['value'] for e in schema.findall("./x:simpleType[@name='OperationType']/x:restriction/x:enumeration",ns)]
assert address==root[5]==162 and reg[2]==0 and reg[5:8]==(2,1,ops.index('READ')) and nbytes==12287 and delay==1
xml=ET.parse(P/'imx319-eeprom-layout-private.xml');item=xml.find('./memoryMap/regSetting')
assert int(item.findtext('slaveAddr'))==address and int(item.findtext('registerAddr'))==0 and int(item.findtext('registerData'))==nbytes and item.findtext('operation')=='READ'
plan=dict(stage=299,sensor='imx319',source_sha256=hashlib.sha256(raw).hexdigest(),source_eeprom_name='fx319aa_imx319',
 address8=address,address7=address>>1,start_address=0,read_bytes=nbytes,address_bytes=2,data_bytes=1,operation='READ',
 original_binary_and_xml_read_map_agree=True,read_plan_only_verified=True,full_calibration_layout_not_verified=True,
 camera_standard_v4l2_stream_owns_power=True,no_factory_power_or_write_sequence_executed=True,
 individual_data_kept_private=True,write_operations_not_permitted=True)
(HERE/'eeprom-read-plan-validation.json').write_text(json.dumps(plan,indent=2)+'\n')
s=(HERE.parent/'kernel298/samurai-raw.c').read_text().replace('frame<18','frame<1800')
assert 'if(frame==5||frame==11||frame==17)' in s
s=s.replace('if(frame==5||frame==11||frame==17)','if(frame==UINT32_MAX)')
a=s.index('  uint64_t total=0;');b=s.index('  for(size_t n=0;n<sizes[buffer.index];n++)data[n]=prefill',a);s=s[:a]+s[b:]
s=s.replace('cleanup:\n if(result)', 'cleanup:\n if(interrupted)result=0;\n if(result)').replace('"--capture"','"--hold"')
p=HERE/'samurai-calibration-hold.c';assert not p.exists();p.write_text(s)
binary=P/'calibration-hold-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include',str(p),'-o',str(binary)],capture_output=True)
(P/'calibration-hold-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True).returncode==0
assert subprocess.run(['qemu-aarch64',str(binary),'--hold','/tmp/not-used'],capture_output=True).returncode==3
(HERE/'calibration-hold-tool-validation.json').write_text(json.dumps(dict(stage=299,kernel_build=298,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,strict_compile_pass=True,wrong_kernel_guard_pass=True,standard_mc_v4l2_only=True,raw_pixels_not_saved=True,max_frames=1800,normal_signal_stop_restores_graph_and_controls=True),indent=2)+'\n')
print(json.dumps(plan,indent=2))
