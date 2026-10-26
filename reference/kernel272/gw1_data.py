"""Read only the two fixed same-handset sensor descriptions already cross-checked in270."""
from pathlib import Path
import hashlib,json,struct

class Description:
    def __init__(self, variant):
        assert variant in ['qtech','sunny']
        proofs=json.loads(Path(__file__).resolve().parents[1].joinpath('kernel270/gw1-metadata-validation.json').read_text())
        proof=next(x for x in proofs['modules'] if x['module']==variant)
        self.path=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins')/('com.qti.sensormodule.'+variant+'_s5kgw1.bin')
        self.raw=self.path.read_bytes();assert hashlib.sha256(self.raw).hexdigest()==proof['source_sha256']
        table,count=struct.unpack_from('<II',self.raw,0x98);assert count==3
        self.sections=[struct.unpack_from('<QQQ',self.raw,table+i*24) for i in range(count)]
        _,so,ss=self.sections[0];_,self.base,size=self.sections[1];self.entries={}
        for pos in range(so,so+ss,72):
            uid=struct.unpack_from('<Q',self.raw,pos)[0];name=self.raw[pos+8:pos+40].split(b'\0')[0].decode()
            offset,length=struct.unpack_from('<QQ',self.raw,pos+56);assert offset<=size and length<=size-offset
            self.entries[uid]=dict(name=name,offset=offset,size=length,position=pos)
    def uid(self,name):
        ids=[i for i,x in self.entries.items() if x['name']==name];assert len(ids)==1,(name,ids)
        return ids[0]
    def payload(self,uid,name=None):
        x=self.entries[uid];assert name is None or x['name']==name
        return self.raw[self.base+x['offset']:self.base+x['offset']+x['size']]
    def words(self,uid,name=None):
        b=self.payload(uid,name);assert len(b)%8==0
        return struct.unpack('<'+'Q'*(len(b)//8),b)
    def regs(self,uid,count):
        b=self.payload(uid,'regSetting');assert len(b)==count*80
        result=[]
        for off in range(0,len(b),80):
            f=struct.unpack_from('<10Q',b,off);assert f[0]==0 and f[5]==2 and f[6] in [1,2] and f[7] in [0,1,2]
            def values(uid,name,n):
                a=self.payload(uid,name);assert len(a)==((n*4+7)//8)*8 and not any(a[n*4:])
                return list(struct.unpack_from('<'+'I'*n,a))
            result.append(dict(address=f[2],address_bytes=2,value_bytes=f[6],operation=['WRITE','WRITE_BURST','WRITE_SEQUENTIAL'][f[7]],
                               values=values(f[4],'registerData',f[3]),delays_us=values(f[9],'delayUs',f[8])))
        return result
