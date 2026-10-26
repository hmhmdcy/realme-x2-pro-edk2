"""Bounded vendor-reader cross-check on an analysis-only resolution subtree."""
from pathlib import Path
import hashlib,json,os,resource,shutil,signal,struct,subprocess,xml.etree.ElementTree as ET
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel217');old=Path('/home/cy122/x2pro-linux/parser-k117');work=Path('/home/cy122/x2pro-linux/parser-k217-modes');assert not work.exists();work.mkdir(mode=0o700)
schema=work/'api/sensor';schema.parent.mkdir();shutil.copytree(old/'api/sensor',schema);ns={'x':'http://www.w3.org/2001/XMLSchema'}
tree=ET.parse(schema/'camxsensordriver.xsd');root_sequence=tree.find("./x:complexType[@name='SensorDriverData']/x:sequence",ns);assert root_sequence is not None
resolution=next(node for node in root_sequence if node.attrib.get('name')=='resolutionInfo')
for node in list(root_sequence):root_sequence.remove(node)
root_sequence.append(resolution)
mode_sequence=tree.find("./x:complexType[@name='ResolutionData']/x:sequence",ns);names=[node.attrib.get('name') for node in mode_sequence];assert names[-2:]==['ADCReadoutTime','mipiFlags']
for node in list(mode_sequence)[-2:]:mode_sequence.remove(node)
ET.register_namespace('xs',ns['x']);tree.write(schema/'camxsensordriver.xsd',encoding='utf-8',xml_declaration=True)
source=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx471.bin');original=source.read_bytes();data=bytearray(original)
_,symbols,symbol_size=struct.unpack_from('<QQQ',data,0xa0);_,data_offset,data_size=struct.unpack_from('<QQQ',data,0xb8)
for offset in range(symbols,symbols+symbol_size,72):
    ident=struct.unpack_from('<Q',data,offset)[0];name=data[offset+8:offset+40].split(b'\0')[0]
    if ident==14:
        assert name==b'resolutionInfo';resolution_offset,resolution_size=struct.unpack_from('<QQ',data,offset+56);assert resolution_size==32
for offset in range(symbols,symbols+symbol_size,72):
    name=data[offset+8:offset+40].split(b'\0')[0]
    if name==b'sensorDriverData':struct.pack_into('<QQ',data,offset+56,resolution_offset,resolution_size)
    elif struct.unpack_from('<I',data,offset+40)[0]==1:struct.pack_into('<I',data,offset+40,0)
analysis=work/'imx471-resolution-analysis.bin';analysis.write_bytes(data);dest=work/'xml';dest.mkdir()
for path in [work,*work.rglob('*')]:os.chown(path,1000,1000)
def limits():
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(5,5));resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,16*1024**2))
args=['stdbuf','-oL','-eL',str(old/'ParameterParser'),str(dest),'x',str(schema),'-b'+str(analysis)]
with (private/'vendor-mode-crosscheck-private.log').open('xb') as log:
    process=subprocess.Popen(args,cwd=work,env=dict(os.environ,LD_LIBRARY_PATH=str(old/'runtime/lib')),user=1000,group=1000,start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=log,preexec_fn=limits)
    timed_out=False
    try:process.wait(timeout=8)
    except subprocess.TimeoutExpired:timed_out=True;os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
assert source.read_bytes()==original
xmls=sorted(dest.glob('*.xml'))
for path in xmls:shutil.copyfile(path,private/('vendor-'+path.name))
record=dict(stage=217,analysis_copy_only=True,source_factory_bin_unchanged=True,source_subtree='ResolutionInformation32 bytes + ResolutionData3x256 bytes',analysis_schema_omits_two_absent_tail_fields=True,vendor_reader_exit=process.returncode,timed_out=timed_out,xml_files=[p.name for p in xmls],hardware_registers_not_written=True)
(private/'vendor-mode-crosscheck-result-private.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));print((private/'vendor-mode-crosscheck-private.log').read_text()[-1500:])
