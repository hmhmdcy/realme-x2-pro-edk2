"""Local SM8150 PD10 inspection: six MSB bytes followed by twelve LSB bits.

This is an observed memory layout, not a reserved upstream FourCC definition.
The decoder keeps ten-bit values and ignores the four reserved high bits.
"""
import struct,zlib
def components(raw,width=160,height=120,stride=768):
 if width%2 or height%2 or width<2 or height<2 or stride<width*4 or len(raw)<stride*(height//2):raise ValueError('PD10 geometry')
 groups=[];reserved=0
 for row in range(height//2):
  for col in range(width//2):
   at=row*stride+col*8;msb=raw[at:at+6];low=int.from_bytes(raw[at+6:at+8],'little')
   reserved+=bool(low&0xf000);groups.append(tuple((msb[i]<<2)|((low>>(i*2))&3) for i in range(6)))
 return groups,reserved
def planes(raw,width=160,height=120,stride=768,order=(0,2,1,3)):
 groups,reserved=components(raw,width,height,stride);y=[0]*(width*height);u=[];v=[]
 for n,g in enumerate(groups):
  row,col=divmod(n,width//2)
  for pos,field in enumerate(order):dy,dx=divmod(pos,2);y[(row*2+dy)*width+col*2+dx]=g[field]
  u.append(g[4]);v.append(g[5])
 return y,u,v,reserved
def render(y,u,v,width,height,path,scale=1,depth=10):
 if len(y)!=width*height or len(u)!=len(v) or len(u)!=width*height//4:raise ValueError('planes')
 shift=depth-8;rgb=[];clamp=lambda x:max(0,min(255,x))
 for row in range(height):
  line=bytearray()
  for col in range(width):
   yy=y[row*width+col]>>shift;at=(row//2)*(width//2)+col//2;cb=(u[at]>>shift)-128;cr=(v[at]>>shift)-128
   pixel=bytes((clamp(yy+((359*cr+128)>>8)),clamp(yy-((88*cb+183*cr+128)>>8)),clamp(yy+((454*cb+128)>>8))))
   line.extend(pixel*scale)
  rgb.extend([b'\0'+bytes(line)]*scale)
 def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',width*scale,height*scale,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rgb)))+chunk(b'IEND',b''))
