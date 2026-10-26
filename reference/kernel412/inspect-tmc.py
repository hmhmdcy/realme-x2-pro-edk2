"""Inspect pinned TMC11 schema and bounded target version references."""
from pathlib import Path
import hashlib,importlib.util,json,struct,subprocess,xml.etree.ElementTree as ET
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
state=json.loads((HERE.parent/'kernel411/source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
state.update(stage=412,source_unchanged_from411=True,tmc11_recovery_pending=True,phone_accessed=False,new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';rev='9f17f1b568626b393e785b369c5dc94543774d7a'
paths=['chi-cdk/api/chromatix/XSD/isp/tmc_1_1_0.xsd','camx/src/hwl/iqinterpolation/tmc11interpolation.cpp',
       'camx/src/hwl/iqinterpolation/tmc11interpolation.h','camx/src/hwl/ispiqmodule/camxswtmc11.cpp',
       'camx/src/hwl/ispiqmodule/camxipeltm13.cpp','camx/src/hwl/ispiqmodule/camxifegtm10.cpp']
out=P/'sources';out.mkdir(exist_ok=True);rows=[]
for path in paths:
    raw=subprocess.check_output(['git','-C',repo,'show',rev+':'+path],timeout=45);(out/Path(path).name).write_bytes(raw)
    rows.append(dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),url='https://github.com/bjzhou/CamxChi/blob/'+rev+'/'+path))
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=412,commit=rev,files=rows),indent=2)+'\n')
schema=ET.parse(out/'tmc_1_1_0.xsd');ns={'x':'http://www.w3.org/2001/XMLSchema'}
for node in schema.findall('x:complexType',ns):
    elements=[]
    for e in node.findall('x:sequence/x:element',ns):
        attrs={a.attrib['name']:a.attrib.get('fixed',a.attrib.get('default')) for a in e.findall('.//x:attribute',ns)}
        elements.append((e.attrib['name'],e.attrib.get('type'),attrs.get('length'),attrs.get('tool_hint',attrs.get('type'))))
    print(node.attrib['name'],elements)
hal=P.parent/'kernel281/camera.qcom.so-private';raw=hal.read_bytes();marker=raw.index(b'Unknown SWTMCVersion');start=raw.rfind(b'\0',0,marker)+1
print('version diagnostic start',hex(start))
refs=[]
phoff=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54)
for i in range(count):
    kind,flags,off,va,pa,length,mem,align=struct.unpack_from('<II6Q',raw,phoff+i*stride)
    if kind!=1 or not flags&1:continue
    for pos in range(0,length-32,4):
        word=struct.unpack_from('<I',raw,off+pos)[0]
        if word&0x9f000000!=0x90000000:continue
        imm=((word>>5)&0x7ffff)<<2 | ((word>>29)&3)
        if imm&(1<<20):imm-=1<<21
        page=((va+pos)&~4095)+(imm<<12);rd=word&31
        if page!=start&~4095:continue
        for delta in range(4,32,4):
            add=struct.unpack_from('<I',raw,off+pos+delta)[0]
            if add&0xff000000==0x91000000 and (add>>5)&31==rd and not add&(1<<22):
                address=page+((add>>10)&4095)
                if address==start:refs.append(va+pos)
(P/'version-diagnostic-refs-private.json').write_text(json.dumps(refs)+'\n');print('version diagnostic code refs',[hex(r) for r in refs])
for address in refs:
    (P/('version-near-'+hex(address)+'-private.asm')).write_bytes(subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(address-500),'--stop-address='+hex(address+650),str(hal)]))
