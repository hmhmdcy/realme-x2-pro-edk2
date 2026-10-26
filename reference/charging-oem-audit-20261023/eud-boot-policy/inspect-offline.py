"""Read actual cached Image/DT/scripts and selected source only; no devices/build."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess,sys,zlib
HERE=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-boot-policy-private')
PRIVATE.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
image=Path('/mnt/e/edk2-samurai-out/kernel363/Image-k363-private')
assert sha(image)=='15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468'
archives=[];raw=image.read_bytes()
for match in re.finditer(b'\x1f\x8b\x08',raw):
 try:
  d=zlib.decompressobj(16+zlib.MAX_WBITS);b=d.decompress(raw[match.start():],64*1024*1024)
  if b.startswith((b'070701',b'070702')) and b'TRAILER!!!' in b:archives.append(b)
 except zlib.error:pass
assert len(archives)==1
b=archives[0];pos=0;files={}
while pos+110<=len(b):
 h=b[pos:pos+110];assert h[:6] in [b'070701',b'070702']
 v=[int(h[6+i*8:14+i*8],16) for i in range(13)]
 size,namesize=v[6],v[11];name=b[pos+110:pos+110+namesize-1].decode().removeprefix('./')
 start=(pos+110+namesize+3)&~3
 if name=='TRAILER!!!':break
 files[name]=b[start:start+size];pos=(start+size+3)&~3
scripts={}
for name in ['init','usr/sbin/samurai-rootfs','usr/sbin/samurai-usb']:
 p=PRIVATE/name.replace('/','--');p.write_bytes(files[name]);scripts[name]=dict(private_path=str(p),sha256=sha(p),bytes=p.stat().st_size)
existing_mount=any(line.split()[4]=='/mnt/samurai-full282' for line in Path('/proc/self/mountinfo').read_text().splitlines())
cache=HERE.parent/'apsd-integration/current-r7'
manifest=json.loads((cache/'source-manifest.json').read_text())
linkage=json.loads((cache/'image-source-linkage.json').read_text())
filemap={x['relative_path']:x for x in manifest['files']}
basemap={x['path']:x for x in linkage['comparisons']}
source=cache/'snapshots'
paths=['drivers/tty/serial/eud.c','drivers/tty/serial/eud_earlycon.c','drivers/usb/dwc3/core.c',
 'drivers/usb/dwc3/dwc3-qcom.c','drivers/usb/dwc3/dwc3-qcom-legacy.c',
 'drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c','arch/arm64/boot/dts/qcom/sm8150-samurai.dts']
sources={}
for name in paths:
 p=source/name.replace('/','--');data=p.read_bytes();assert len(data)<220000
 assert sha(p)==filemap[name]['sha256']
 dst=HERE/name.replace('/','--');dst.write_bytes(data)
 link=basemap.get(name)
 sources[name]=dict(sha256=sha(p),base_sha256=link.get('base_sha256') if link else None,
  matches_image_source=link.get('byte_equal_to_original_image_source') if link else None,bytes=len(data))
dtb=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-boot/samurai-charging-private.dtb')
dts=subprocess.check_output(['dtc','-I','dtb','-O','dts',str(dtb)],stderr=subprocess.DEVNULL)
(PRIVATE/'current-native.dts').write_bytes(dts)
assert sha(dtb)=='c559d2c4c9a83e85473b1b24724bb8938f1084bd3efcae9c4b67f37c2a4c4503'
repo=Path('/home/cy122/edk2-samurai/repo');firmware={}
for name in ['Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c',
 'Platform/Realme/sm8150/EudLogDxe/EudLogDxe.c','Platform/Realme/sm8150/Library/EudSerialPortLib/EudSerialPortLib.c']:
 p=repo/name;target=HERE/p.name;target.write_bytes(p.read_bytes())
 firmware[name]=dict(source_path=str(p),sha256=sha(p),bytes=p.stat().st_size)
result=dict(passed=True,image_sha256=sha(image),embedded_scripts=scripts,native_dtb_path=str(dtb),native_dtb_sha256=sha(dtb),sources=sources,firmware_sources=firmware,
 source_cache_manifest_sha256=sha(cache/'source-manifest.json'),image_linkage_sha256=sha(cache/'image-source-linkage.json'),existing_source_mount=existing_mount,source_mount_attempted=False,
 source=str(source),phone_accessed=False,ssh_executed=False,usb_accessed=False,sdk_invoked=False,shared_writes=False)
(HERE/'inspection.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,scripts=scripts,native_dtb_sha256=sha(dtb),source=str(source))))
