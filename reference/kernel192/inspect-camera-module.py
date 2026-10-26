from pathlib import Path
import struct,xml.etree.ElementTree as E,json
p=Path('/mnt/e/edk2-samurai-out/kernel115/vendor-camera-bins/com.qti.sensormodule.sunny_imx471.bin');b=p.read_bytes();_,so,ss=struct.unpack_from('<QQQ',b,0xa0);_,do,ds=struct.unpack_from('<QQQ',b,0xb8)
for off in range(so,so+ss,72):
 ident=struct.unpack_from('<Q',b,off)[0]
 if not 1063<=ident<=1085:continue
 name=b[off+8:off+40].split(b'\0')[0].decode();d,sz=struct.unpack_from('<QQ',b,off+56)
 print(ident,name,sz,'words',struct.unpack('<'+'Q'*(sz//8),b[do+d:do+d+sz]) if sz%8==0 and sz<400 else None)
root=Path('/mnt/e/edk2-samurai-out/kernel117/CamxChi/chi-cdk/api/sensor');ns={'x':'http://www.w3.org/2001/XMLSchema'}
for fn in ['camxmoduleconfig.xsd','camxsensorcommon.xsd']:
 tree=E.parse(root/fn)
 for name in ['CSIInformation','ModuleConfiguration','I2CFrequencyMode','I2CRegAddrDataType']:
  for node in tree.findall(".//*[@name='"+name+"']"):
   print(name,[e.attrib for e in node.findall('./x:sequence/x:element',ns) or node.findall('.//x:enumeration',ns)])
kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');lines=(kernel/'drivers/media/i2c/imx471.c').read_text().splitlines()
print('\n'.join(lines[210:300]));print('\n'.join(lines[730:808]))
