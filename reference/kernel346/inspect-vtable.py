from pathlib import Path
import json,struct,subprocess
import host
P=host.PRIVATE;path=P.parent/'kernel328/stats-source/com.qti.stats.aec.so';raw=path.read_bytes()
offset=struct.unpack_from('<Q',raw,40)[0];stride,count=struct.unpack_from('<HH',raw,58);relocations={};relr=set()
for i in range(count):
 section=struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*stride)
 if section[1] in [19,0x6fffff00]:
  where=0
  for pos in range(section[4],section[4]+section[5],8):
   value=struct.unpack_from('<Q',raw,pos)[0]
   if not value&1:relr.add(value);where=value+8
   else:
    for bit in range(1,64):
     if value&(1<<bit):relr.add(where+(bit-1)*8)
    where+=63*8
 if section[1]!=4:continue
 for pos in range(section[4],section[4]+section[5],section[9]):
  address,info,addend=struct.unpack_from('<QQq',raw,pos)
  if info&0xffffffff==1027:relocations[address]=addend
pattern=struct.pack('<3Q',0x1def8,0x1df00,0x1df08);at=raw.index(pattern);assert raw.find(pattern,at+1)==-1
phoff=struct.unpack_from('<Q',raw,32)[0];phstride,phcount=struct.unpack_from('<HH',raw,54)
segments=[struct.unpack_from('<II6Q',raw,phoff+i*phstride) for i in range(phcount)]
segment=next(s for s in segments if s[0]==1 and s[2]<=at<s[2]+s[5]);pointer=segment[3]+at-segment[2]
target=struct.unpack_from('<Q',raw,at+264)[0];assert target==0x1e300
assert all(pointer+offset in relr for offset in [0,8,16,264])
proof=dict(caller_virtual_offset=264,vtable_start=hex(pointer),resolved_method_address=hex(target),resolved_method='CAECCoreDataManager::getHDR3Enable()',
 supports_chosen_policy_flag_name=True,source='retained ELF raw vtable words covered by RELR relocations, plus recovered symbols')
(P/'hdr3-policy-binding-private.json').write_text(json.dumps(proof,indent=2)+'\n')
(Path(__file__).resolve().parent/'hdr3-policy-binding-validation.json').write_text(json.dumps(dict(stage=346,**proof,passed=True),indent=2)+'\n')
print(json.dumps(proof,indent=2))
for label,start,end in [('hdr3-getter',0x1e300,0x1e318),('ev-knee',0x2d350,0x2d508)]:
 (P/(label+'-private.asm')).write_bytes(subprocess.check_output(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(end),str(path)]))
