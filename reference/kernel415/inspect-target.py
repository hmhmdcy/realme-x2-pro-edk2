"""Inspect bounded original policy, metadata, and pinned repository sources."""
from pathlib import Path
import hashlib,importlib.util,json,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
state=json.loads((HERE.parent/'kernel414/source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
state.update(stage=415,source_unchanged_from414=True,phone_accessed=False,new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';rev='9f17f1b568626b393e785b369c5dc94543774d7a'
paths=['camx/src/hwl/ife/camxifenode.cpp','camx/src/hwl/ispiqmodule/camxispiqmodule.h',
       'camx/src/hwl/isphwsetting/pipeline/ife/camxtitan170ife.cpp','camx/src/hwl/ipe/camxipenode.cpp']
out=P/'sources';out.mkdir(exist_ok=True);rows=[]
for path in paths:
    raw=subprocess.check_output(['git','-C',repo,'show',rev+':'+path],timeout=45)
    (out/Path(path).name).write_bytes(raw)
    rows.append(dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),url='https://github.com/bjzhou/CamxChi/blob/'+rev+'/'+path))
    lines=raw.decode(errors='replace').splitlines()
    for i,line in enumerate(lines):
        if any(v in line for v in ['enabledTMCversion','SWTMC11::Create','PropertyIDIFEADRC','pADRCData']):
            print(Path(path).name,i+1,line.strip()[:170])
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=415,commit=rev,new_files=rows,prior_manifest='../kernel412/primary-sources.json'),indent=2)+'\n')
hal=P.parent/'kernel281/camera.qcom.so-private';raw=hal.read_bytes()
markers=[b'IPE LTM : using TMC 10',b'IPE LTM : using TMC 11',b'Unknown SWTMCVersion']
addresses={}
for marker in markers:
    at=raw.find(marker)
    if at>=0:addresses[raw.rfind(b'\0',0,at)+1]=marker.decode()
found={v:[] for v in addresses.values()}
phoff=struct.unpack_from('<Q',raw,32)[0];stride,count=struct.unpack_from('<HH',raw,54)
for i in range(count):
    kind,flags,off,va,pa,length,mem,align=struct.unpack_from('<II6Q',raw,phoff+i*stride)
    if kind!=1 or not flags&1:continue
    for pos in range(0,length-32,4):
        word=struct.unpack_from('<I',raw,off+pos)[0]
        if word&0x9f000000!=0x90000000:continue
        imm=((word>>5)&0x7ffff)<<2|((word>>29)&3)
        if imm&(1<<20):imm-=1<<21
        page=((va+pos)&~4095)+(imm<<12);rd=word&31
        if not any(page==a&~4095 for a in addresses):continue
        for delta in range(4,36,4):
            add=struct.unpack_from('<I',raw,off+pos+delta)[0]
            if add&0xff000000==0x91000000 and (add>>5)&31==rd and not add&(1<<22):
                address=page+((add>>10)&4095)
                if address in addresses:found[addresses[address]].append(va+pos)
(P/'policy-string-refs-private.json').write_text(json.dumps(found,indent=2)+'\n')
windows=[(0x383728,0x383cdc),(0x384de8,0x384dfc),(0x2dffe4,0x2e01f8),
         (0x2d0050,0x2d015c),(0x2cfa70,0x2cfaa0),(0x360088,0x360154)]
for values in found.values():
    for at in values:windows.append((at-500,at+300))
for start,end in windows:
    q=subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(end),str(hal)])
    (P/('policy-'+hex(start)+'-private.asm')).write_bytes(q)
print({k:[hex(a) for a in v] for k,v in found.items()})
