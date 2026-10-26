"""Exploratory parameterized bypass geometry; not a kernel/runtime encoder."""
import struct

def encode(width,height,port=8,cores=1):
 n=(width+327)//328;n=(n+cores-1)//cores*cores
 b=bytearray(2268+624*n)
 def h(off,v):struct.pack_into('<H',b,off,v&65535)
 def u(off,v):struct.pack_into('<I',b,off,v&0xffffffff)
 def module(base,length,grid,first=0,left=-1,horizontal=False,fetch=0,fetch_last=0):
  h(base+32,1);h(base+34,length-1);h(base+36,left);h(base+38,1 if horizontal else 2);h(base+42,24)
  h(base+84,grid);h(base+86,65536//grid);h(base+88,first//grid);h(base+90,first%grid);h(base+92,(first%grid)*(65536//grid))
  for off in [130,162,194,226]:
   chroma=off==(162 if port==9 else 226)
   h(base+off,64 if chroma else 32);h(base+off+2,int(chroma));h(base+off+4,length);h(base+off+10,3)
  for off in [278,286,290,294,298,302,310,318]:h(base+off,length-1)
  for off in [282,306,314]:h(base+off,length//2-1)
  if horizontal:
   h(base+276,first-fetch);h(base+278,first-fetch+length-1);h(base+282,fetch_last-fetch)
 h(2 if port==9 else 4,20);u(20,1)
 module(24,height,max(27,(height+8)//9))
 h(376,height-1);h(396 if port==9 else 392,height-1)
 u(424,22);h(428,n);u(432,2248)
 for i in range(n):
  index=n-i-1;first=(width*index//n)&~1;last=((width*(index+1)//n)&~1)-1
  f=max(first-4,0);end=min(last+4,width-1);size=last-first+1;s=2268+624*i
  h(s+4,f);h(s+6,end);h(s+(24 if port==9 else 20),first);h(s+(26 if port==9 else 22),last)
  h(s+44,int(first==0)|(int(last==width-1)<<8))
  module(s+48,size,max(27,(width+11)//12),first,1 if first else -1,True,f,end)
  h(s+568,first);u(s+576,(first-width//2)**2+(height//2)**2);h(s+580,first-width//2);h(s+582,-height//2)
  u(s+600,(end-f+1)*height);h(s+618,257);h(s+620,257)
 return bytes(b)
