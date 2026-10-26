"""Compare the caller's actual LTM selector against native region interpolation."""
from pathlib import Path
import importlib.util,json,struct,subprocess,yaml
from unicorn.arm64_const import *
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel423')
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
module('storage284',HERE.parent/'kernel284/storage.py').mounted_build();h=module('hal380',HERE.parent/'kernel380/hal-machine.py');target=h.Machine()
leaves=yaml.safe_load((P/'factory-s5kgw1-private.yaml').read_bytes())['modes'][0]['ipe_tone']['ltm_regions']
records=[];expected=[]
for index in range(len(leaves)-1):
 for ratio in [0,.25,.5,.75,1]:
  a=struct.pack('<179f',*leaves[index]['data']);b=struct.pack('<179f',*leaves[index+1]['data']);u=target.u
  left,right,out=h.DATA+0x10000,h.DATA+0x20000,h.DATA+0x30000
  u.mem_write(left,a);u.mem_write(right,b);u.mem_write(out,bytes([0xa7])*748)
  u.reg_write(UC_ARM64_REG_S0,struct.unpack('<I',struct.pack('<f',ratio))[0])
  assert target.call(0x49e980,left,right,out)==1
  assert bytes(u.mem_read(out+716,32))==bytes([0xa7])*32
  records.append(a+b+struct.pack('<f',ratio));expected.append(bytes(u.mem_read(out,716)))
cpp=(HERE/'ipe_tone_profile.cpp').read_text();a=cpp.index('float blend(');b=cpp.index('template<class T> void store(',a)
code='''#include <array>
#include <vector>
#include <cstdint>
#include <climits>
#include <cmath>
#include <cassert>
#include <iostream>
template<size_t N> struct ToneAecRegion {std::array<float,4> trigger;std::array<float,N> data;};
'''+cpp[a:b]+'''int main(){std::vector<ToneAecRegion<179>> r(2);r[0].trigger={0,0,0,0};r[1].trigger={1,1,1,1};float ratio;while(std::cin.read(reinterpret_cast<char*>(r[0].data.data()),716)){assert(std::cin.read(reinterpret_cast<char*>(r[1].data.data()),716));assert(std::cin.read(reinterpret_cast<char*>(&ratio),4));std::array<float,179> out;assert(select(r,0,ratio,&out));std::cout.write(reinterpret_cast<const char*>(out.data()),716);}}
'''
(P/'interpolation.cpp').write_text(code)
q=subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie',str(P/'interpolation.cpp'),'-o',str(P/'interpolation')],capture_output=True);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(P/'interpolation')],input=b''.join(records),capture_output=True);assert not q.returncode,q.stderr.decode()
wanted=b''.join(expected);assert len(q.stdout)==len(wanted)
(P/'interpolation-actual-private.bin').write_bytes(q.stdout);(P/'interpolation-target-private.bin').write_bytes(wanted)
diff=sum(a!=b for a,b in zip(q.stdout,wanted))
r=dict(stage=423,actual_caller_blend_and_select_extracted=True,selected_main_ltm_adjacent_pairs=len(leaves)-1,cases=len(records),compared_bytes=len(wanted),different_bytes=diff,native_instructions=target.instructions,host_asan_ubsan=True,passed=diff==0)
(HERE/'interpolation-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));assert r['passed']
