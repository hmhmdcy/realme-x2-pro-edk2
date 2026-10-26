"""Read bounded camera mounting properties from the preserved DTBO, without modifying it."""
from pathlib import Path
import hashlib,json,struct
import host
R=Path(__file__).parent;p=host.PRIVATE.parent/'kernel248/linux-return-partitions/dtbo.img';data=p.read_bytes();rows=[];offset=0;trees=0
while True:
 base=data.find(b'\xd0\x0d\xfe\xed',offset)
 if base<0:break
 offset=base+4
 if base+40>len(data):continue
 h=struct.unpack_from('>10I',data,base);_,total,ofs,ostr,_,ver,_,_,nstr,nstruct=h
 if total<40 or base+total>len(data) or ofs+nstruct>total or ostr+nstr>total or ver<16:continue
 blob=data[base:base+total];strings=blob[ostr:ostr+nstr];pos=ofs;stack=[];properties=[]
 try:
  while pos<ofs+nstruct:
   token=struct.unpack_from('>I',blob,pos)[0];pos+=4
   if token==1:
    end=blob.index(0,pos);stack.append(blob[pos:end].decode(errors='replace'));pos=(end+4)&~3
   elif token==2:stack.pop()
   elif token==3:
    size,nameoff=struct.unpack_from('>II',blob,pos);pos+=8;assert pos+size<=total and nameoff<len(strings)
    end=strings.index(0,nameoff);name=strings[nameoff:end].decode();value=blob[pos:pos+size];pos=(pos+size+3)&~3
    path='/'.join(stack)
    if ('cam' in path.lower() or 'sensor' in path.lower()) and any(x in name.lower() for x in ['mount-angle','sensor-position','rotation','orientation','cell-index','cci-master']):
     if len(value)==4:properties.append(dict(node=path,property=name,value=struct.unpack('>I',value)[0]))
   elif token==4:continue
   elif token==9:break
   else:raise ValueError(token)
 except (AssertionError,ValueError,IndexError,struct.error):continue
 trees+=1
 if properties:rows.append(dict(tree=trees,properties=properties))
report=dict(stage=266,source_sha256=hashlib.sha256(data).hexdigest(),valid_fdt_trees=trees,camera_mounting=rows,source_unchanged=hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(data).digest())
(host.PRIVATE/'preserved-dtbo-mounting-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

