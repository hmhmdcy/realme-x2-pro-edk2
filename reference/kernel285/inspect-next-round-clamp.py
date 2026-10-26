"""Fetch pinned layout references privately and inspect the actual HAL path table."""
from pathlib import Path
import hashlib,json,struct,subprocess,urllib.request

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel285')
COMMIT='9f17f1b568626b393e785b369c5dc94543774d7a'
paths=['camx/src/hwl/isphwsetting/titan17x/camxiferoundclamp11titan17x.cpp',
       'camx/src/hwl/isphwsetting/titan17x/camxiferoundclamp11titan17x.h',
       'camx/src/hwl/iqsetting/cst12setting.h']
sources={}
for name in paths:
    url=f'https://raw.githubusercontent.com/bjzhou/CamxChi/{COMMIT}/{name}'
    target=PRIVATE/('reference-'+Path(name).name+'-private')
    if target.exists():data=target.read_bytes()
    else:
        data=urllib.request.urlopen(url,timeout=30).read();target.write_bytes(data)
    sources[name]=dict(url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
(PRIVATE/'next-round-clamp-reference-sources-private.json').write_text(json.dumps(sources,indent=2)+'\n')
hal=Path('/mnt/e/edk2-samurai-out/kernel281/camera.qcom.so-private')
target=PRIVATE/'round-clamp-create-disassembly-private.txt'
if not target.exists():
    p=subprocess.run(['aarch64-linux-gnu-objdump','-d','--start-address=0x332290','--stop-address=0x332618',str(hal)],text=True,capture_output=True,check=True)
    target.write_text(p.stdout)
data=hal.read_bytes()
assert hashlib.sha256(data).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
off=struct.unpack_from('<Q',data,32)[0];size,count=struct.unpack_from('<HH',data,54)
loads=[]
for i in range(count):
    kind,flags,start,vaddr,physical,length,memsize,align=struct.unpack_from('<IIQQQQQQ',data,off+i*size)
    if kind==1:loads.append((vaddr,start,length))
def read(address,size):
    for base,start,length in loads:
        if base<=address and address+size<=base+length:return data[start+address-base:start+address-base+size]
    raise AssertionError(hex(address))
table=list(read(0xd38d6,7))
targets=[0x333910+n*4 for n in table]
assert targets[0]==0x333910,targets
for address,instruction in {0x3338ec:0xb940b269,0x333918:0x5281c717,0x33391c:0x5281c301,0x333924:0x52800042}.items():
    assert struct.unpack('<I',read(address,4))[0]==instruction
facts=dict(stage=285,hal_sha256=hashlib.sha256(data).hexdigest(),static_only=True,
           output_path_table={str(i):hex(t) for i,t in enumerate(targets)},
           video_full_path=0,video_full_luma_pair='0xe18/0xe1c',video_full_chroma_pair='0xe38/0xe3c',
           reference_output_bit_widths=[8,10],reference_round_bits='10 - output bits',
           reference_clamp_is_output_depth=True,
           note='Do not reuse CST 10-bit clamp endpoints directly as the output-depth clamp. Confirm masks, order and bit-depth semantics against actual HAL before implementation.',
           not_implemented=True,not_hardware_validated=True,
           source_references=sources)
(ROOT/'next-round-clamp-facts-validation.json').write_text(json.dumps(facts,indent=2)+'\n')
print(json.dumps(dict(reference_files=[dict(path=n,**m) for n,m in sources.items()],
                     original_implementation_private=True,round_clamp_not_implemented=True),indent=2))
