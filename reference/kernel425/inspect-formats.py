from pathlib import Path
import importlib.util,json,re,struct,subprocess
from unicorn.arm64_const import *
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build()
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';rev='9f17f1b568626b393e785b369c5dc94543774d7a'
names=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',rev],text=True).splitlines()
selected=[n for n in names if Path(n).name in ['camxformats.h','camximageformatutils.h','camximageformatutils.cpp','camxcslicpdefs.h','ipe_data.h','ipeStripingLib.h']]
out=P/'sources';out.mkdir(exist_ok=True)
for n in selected:
 raw=subprocess.check_output(['git','-C',repo,'show',rev+':'+n]);(out/Path(n).name).write_bytes(raw)
 lines=raw.decode().splitlines()
 for i,l in enumerate(lines):
  if re.search(r'PD10|enum class Format|IMAGE_FORMAT_PD_10|INPUT_IMAGE_DS4',l):print(n,i+1,l)
h=module('hal380',HERE.parent/'kernel380/hal-machine.py');m=h.Machine();rows=[]
for fmt in range(3,24):
 u=m.u;D=h.DATA;u.mem_write(D,bytes(0x20000));u.mem_write(D+0x10000,struct.pack('<3I',160,120,fmt)+bytes(256));u.mem_write(D+0x4000,bytes([0xa7])*1216)
 for r,v in [(UC_ARM64_REG_X0,D),(UC_ARM64_REG_X1,D+0x4000),(UC_ARM64_REG_X2,D+0x10000),(UC_ARM64_REG_X3,1),(UC_ARM64_REG_X4,0),(UC_ARM64_REG_SP,h.STACK+0xf0000)]:u.reg_write(r,v)
 u.emu_start(0x2e4b88,0x2e4c70,count=200);assert u.reg_read(UC_ARM64_REG_PC)==0x2e4c70
 rows.append(dict(camx_format=fmt,firmware_format=struct.unpack('<I',u.mem_read(D+0x4000+84,4))[0]))
(P/'format-translation-private.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows));print(json.dumps(dict(reference_files=selected,native_translation_fragment=True)))
