from pathlib import Path
import json,os
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k210-baseline/boot-id-private.txt').read_bytes()
p=Path('/usr/lib/modules')/os.uname().release
files=[x for x in p.rglob('*') if x.is_file()]
print(json.dumps(dict(regular_files=len(files),ko_modules=sum(x.name.endswith('.ko') for x in files),non_ko_files=[str(x.relative_to(p)) for x in files if not x.name.endswith('.ko')])))
