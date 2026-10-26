from pathlib import Path
import json, os
root=Path('/var/lib/samurai')
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
print(json.dumps(dict(model=Path('/sys/firmware/devicetree/base/model').read_text().rstrip('\0'),
    same_boot199=boot==(root/'k199-baseline/boot-id-private.txt').read_bytes(),
    same_boot200=boot==(root/'k200-baseline/boot-id-private.txt').read_bytes(),
    kernel183=os.uname().version.startswith('#183 '))))
