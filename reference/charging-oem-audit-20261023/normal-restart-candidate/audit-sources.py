"""Copy only small relevant source excerpts from the actual existing build."""
from pathlib import Path
import hashlib,json,sys
sys.path.insert(0, '/mnt/e/RealmeX2Pro edk2/reference/kernel284')
import storage
HERE=Path(__file__).resolve().parent
source=storage.mounted_build().parent/'source354'
targets={
 'kernel/reboot.c':[(101,107),(280,301),(721,802)],
 'drivers/base/core.c':[(4875,4942)],
 'drivers/base/platform.c':[(1527,1538)],
 'drivers/tty/serial/eud.c':[(619,628),(651,693),(1377,1418)],
}
manifest={}
for name,ranges in targets.items():
 raw=(source/name).read_bytes();lines=raw.decode().splitlines()
 text='Actual source354 / '+name+'\n'
 for lo,hi in ranges:
  text+='\n'+ '\n'.join(f'{i+1}: {lines[i]}' for i in range(lo-1,hi))+'\n'
 target=name.replace('/','--')+'.excerpt.txt'
 (HERE/target).write_text(text,encoding='utf-8')
 manifest[name]={'source_sha256':hashlib.sha256(raw).hexdigest(),
  'source_lines':len(lines),'excerpt':target,'ranges':ranges}
(HERE/'source-excerpts.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
