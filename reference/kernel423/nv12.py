"""Decode limited-range BT.601 NV12 for local inspection; no tone adjustment."""
import struct,zlib
def render(raw,path):
 assert len(raw)==460800
 def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
 rows=bytearray();clamp=lambda n:max(0,min(255,n))
 for y in range(480):
  rows.append(0)
  for x in range(640):
   a=raw[y*640+x]-16;at=307200+(y//2)*640+(x//2)*2;u=raw[at]-128;v=raw[at+1]-128
   rows.extend((clamp((298*a+409*v+128)>>8),clamp((298*a-100*u-208*v+128)>>8),clamp((298*a+516*u+128)>>8)))
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',640,480,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b''))
