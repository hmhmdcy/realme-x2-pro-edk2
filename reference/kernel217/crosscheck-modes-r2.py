"""Keep verified sensor/module context while projecting resolution data for XML."""
from pathlib import Path
import hashlib,json,os,resource,shutil,signal,struct,subprocess,xml.etree.ElementTree as ET
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel217');old=Path('/home/cy122/x2pro-linux/parser-k117');work=Path('/home/cy122/x2pro-linux/parser-k217-modes-r2');assert not work.exists();work.mkdir(mode=0o700)
schema=work/'api/sensor';schema.parent.mkdir();shutil.copytree(old/'api/sensor',schema);ns={'x':'http://www.w3.org/2001/XMLSchema'};ET.register_namespace('xs',ns['x'])
tree=ET.parse(schema/'camxsensordriver.xsd');seq=tree.find("./x:complexType[@name='SensorDriverData']/x:sequence",ns)
kept=[node for node in seq if node.attrib.get('name') in ['module_version','slaveInfo','resolutionInfo']];assert [node.attrib['name'] for node in kept]==['module_version','slaveInfo','resolutionInfo']
for node in list(seq):seq.remove(node)
for node in kept:seq.append(node)
seq=tree.find("./x:complexType[@name='ResolutionData']/x:sequence",ns);assert [node.attrib.get('name') for node in list(seq)[-2:]]==['ADCReadoutTime','mipiFlags']
for node in list(seq)[-2:]:seq.remove(node)
tree.write(schema/'camxsensordriver.xsd',encoding='utf-8',xml_declaration=True)
tree=ET.parse(schema/'camxmoduleconfig.xsd');seq=tree.find("./x:complexType[@name='ModuleConfiguration']/x:sequence",ns);assert [node.attrib.get('name') for node in list(seq)[:5]]==['cameraId','moduleName','sensorName','sensorSlaveAddress','sensorI2CFrequencyMode']
for node in list(seq)[5:]:seq.remove(node)
tree.write(schema/'camxmoduleconfig.xsd',encoding='utf-8',xml_declaration=True)
source=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx471.bin');original=source.read_bytes();data=bytearray(original)
_,symbols,symbol_size=struct.unpack_from('<QQQ',data,0xa0);_,data_offset,data_size=struct.unpack_from('<QQQ',data,0xb8)
entries={}
for offset in range(symbols,symbols+symbol_size,72):
    ident=struct.unpack_from('<Q',data,offset)[0];name=data[offset+8:offset+40].split(b'\0')[0].decode();relative,size=struct.unpack_from('<QQ',data,offset+56);entries[ident]=dict(name=name,relative=relative,size=size,symbol_offset=offset)
assert entries[1]['name']=='sensorDriverData' and entries[1]['relative']==0 and entries[1]['size']==816
assert entries[14]['name']=='resolutionInfo' and entries[14]['size']==32
projection=original[data_offset:data_offset+128]+original[data_offset+entries[14]['relative']:data_offset+entries[14]['relative']+32];assert len(projection)==160
new_offset=len(data)-data_offset;data.extend(projection);struct.pack_into('<I',data,28,len(data));struct.pack_into('<Q',data,0xb8+16,len(data)-data_offset)
for item in entries.values():
    offset=item['symbol_offset'];name=item['name']
    if name=='sensorDriverData':struct.pack_into('<QQ',data,offset+56,new_offset,160)
    elif name=='moduleConfiguration':struct.pack_into('<Q',data,offset+64,72)
    elif struct.unpack_from('<I',data,offset+40)[0]==1 and name!='cameraModuleData':struct.pack_into('<I',data,offset+40,0)
analysis=work/'imx471-resolution-analysis.bin';analysis.write_bytes(data);dest=work/'xml';dest.mkdir()
for path in [work,*work.rglob('*')]:os.chown(path,1000,1000)
def limits():
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(5,5));resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,16*1024**2))
args=['stdbuf','-oL','-eL',str(old/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(analysis)]
with (private/'vendor-mode-r2-private.log').open('xb') as log:
    process=subprocess.Popen(args,cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=str(old/'runtime/lib')),user=1000,group=1000,start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=log,preexec_fn=limits)
    timed_out=False
    try:process.wait(timeout=8)
    except subprocess.TimeoutExpired:timed_out=True;os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
assert source.read_bytes()==original
xmls=sorted(dest.rglob('*.xml'))
for path in xmls:
    target=private/'vendor-r2-xml'/path.relative_to(dest);target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);shutil.copyfile(path,target)
record=dict(stage=217,analysis_copy_only=True,source_factory_bin_unchanged=True,context_prefix_and_resolution_projection_bytes=160,original_resolution_payload_bytes_unchanged=True,vendor_reader_exit=process.returncode,timed_out=timed_out,xml_files=[str(p.relative_to(dest)) for p in xmls],hardware_registers_not_written=True)
(private/'vendor-mode-r2-result-private.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));print((private/'vendor-mode-r2-private.log').read_text()[-1000:])
