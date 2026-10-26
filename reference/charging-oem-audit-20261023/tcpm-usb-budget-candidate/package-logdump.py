"""Replace only the same-size Image data in the cached R2 FAT; no device access."""
from pathlib import Path
import importlib.util,json,os,subprocess
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('frozen_R2_FAT_helpers',HERE.parent/'tcpm-sink-shutdown-candidate/package-logdump.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OLD=BASE/'tcpm-sink507-r2-logdump-private-01/logdump-tcpm-sink507-r2-private.img'
OUT=BASE/'tcpm-usb-budget508-logdump-private-01'
assert not OUT.exists() and not (HERE/'logdump-package-result.json').exists()
build=json.loads((HERE/'build-result.json').read_bytes());assert build['passed']
for name,digest in build['build']['sources'].items():
 assert m.sha((HERE/json.loads((HERE/'source.json').read_bytes())['sources'][name]['file']).read_bytes())==digest
image=m.pinned(Path(build['build']['Image_path']),build['build']['Image_sha256'])
old=m.pinned(OLD,'3ebf72dedf5ca39ff2ec24cbe491e7c2f5c8c080c753cbb68c4c602b886a7f5c')
fat=m.parse_fat(old);entry=fat['files']['Image']
assert entry['sha256']=='371493db3a9cbd72af6c37bc5ea2f7637ee5fc0dcb8d46c4ac24550599dc082e'
assert len(image)==entry['size']==build['build']['Image_bytes']
new=bytearray(old)
for index,cluster in enumerate(entry['clusters']):
 offset=fat['data_at']+(cluster-2)*fat['bps'];piece=image[index*fat['bps']:(index+1)*fat['bps']]
 new[offset:offset+len(piece)]=piece
parsed=m.parse_fat(new)
assert parsed['files']['Image']['content']==image
assert parsed['files']['SAMURAI.DTB']==fat['files']['SAMURAI.DTB']
assert new[:fat['data_at']]==old[:fat['data_at']]
allowed=set(entry['clusters'])
for offset in range(fat['data_at'],len(old),fat['bps']):
 if (offset-fat['data_at'])//fat['bps']+2 not in allowed:assert new[offset:offset+fat['bps']]==old[offset:offset+fat['bps']]
last=fat['data_at']+(entry['clusters'][-1]-2)*fat['bps']+len(image)%fat['bps']
if len(image)%fat['bps']:assert new[last:last+fat['bps']-len(image)%fat['bps']]==old[last:last+fat['bps']-len(image)%fat['bps']]
tool,digest=m.TOOLS['fsck.fat'];m.pinned(Path(tool),digest)
OUT.mkdir();target=OUT/'logdump-tcpm-usb-budget508-private.img'
with target.open('xb') as stream:stream.write(new);stream.flush();os.fsync(stream.fileno())
assert m.read_bytes(target)==new
check=subprocess.run([tool,'-n',str(target)],capture_output=True,text=True)
(OUT/'fsck.stdout').write_text(check.stdout);(OUT/'fsck.stderr').write_text(check.stderr)
assert check.returncode==0,check.stderr
assert m.read_bytes(target)==new
result={'passed':True,'installed':False,'candidate':{'path':str(target),'sha256':m.sha(new),'bytes':len(new)},
 'base_R2_FAT_sha256':m.sha(old),'Image_sha256':m.sha(image),'Image_bytes':len(image),
 'only_existing_Image_data_changed':True,'allocation_directory_DTB_and_slack_exact':True,
 'readback_exact':True,'fsck_readonly_passed':True,'phone_accessed':False}
(HERE/'logdump-package-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
