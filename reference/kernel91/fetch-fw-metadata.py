from pathlib import Path
import base64,hashlib,json,struct,urllib.request
O=Path('/mnt/e/edk2-samurai-out/kernel91')
url='https://kernel.googlesource.com/pub/scm/linux/kernel/git/firmware/linux-firmware.git/+/refs/tags/20250211/ath10k/WCN3990/hw1.0/firmware-5.bin?format=TEXT'
with urllib.request.urlopen(url,timeout=30) as response: raw=response.read()
data=base64.b64decode(raw,validate=True)
assert data.startswith(b'QCA-ATH10K\0') and len(data)<1024
pos=12; items={}
while pos<len(data):
    key,n=struct.unpack_from('<II',data,pos);pos+=8
    assert n<=len(data)-pos and key not in items
    items[key]=data[pos:pos+n];pos+=(n+3)//4*4
assert pos==len(data) and set(items)<= {0,1,2,5,6}
assert struct.unpack('<I',items[5])[0]==4
assert struct.unpack('<I',items[6])[0]==3
features=int.from_bytes(items[2],'little')
assert features & 0xc0000 == 0xc0000
(O/'firmware-5.bin').write_bytes(data)
report=dict(source_url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
            ie_ids=list(items),features_hex=hex(features),wmi='TLV',htt='TLV',
            code_image=False,otp_image=False,board_data=False)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel91/fw-metadata.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
