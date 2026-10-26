import hashlib,stat
def members(path):
 data=path.read_bytes();pos=0;result={}
 while pos<len(data):
  assert data[pos:pos+6]==b'070701'
  fields=[int(data[pos+6+i*8:pos+14+i*8],16) for i in range(13)]
  inode,mode,uid,gid,nlink,mtime,size,devmajor,devminor,rmajor,rminor,namesize,check=fields
  name=data[pos+110:pos+110+namesize];assert name[-1:]==b'\0'
  name=name[:-1].decode().removeprefix('./');pos=(pos+110+namesize+3)&~3
  body=data[pos:pos+size];assert len(body)==size;pos=(pos+size+3)&~3
  if name=='TRAILER!!!':break
  assert name not in result and not name.startswith('/') and '..' not in name.split('/')
  result[name]=dict(mode=mode,uid=uid,gid=gid,nlink=nlink,size=size,rmajor=rmajor,rminor=rminor,sha256=hashlib.sha256(body).hexdigest())
 assert not any(data[pos:]);return result
def console_ok(items):
 n=items['dev/console'];return stat.S_ISCHR(n['mode']) and stat.S_IMODE(n['mode'])==0o600 and (n['uid'],n['gid'],n['rmajor'],n['rminor'],n['size'])==(0,0,5,1,0)
