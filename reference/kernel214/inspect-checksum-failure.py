from pathlib import Path
import json,re,subprocess
root=Path('/home/cy122/x2pro-linux/libcamera214-root');lines=(root/'usr/bin/abuild').read_text().splitlines()
for index,line in enumerate(lines):
    if re.search(r'^default_fetch\(\)',line):print('\n'.join(lines[index:index+105]))
print(subprocess.check_output(['chroot',str(root),'/usr/bin/sha512sum','/work/libcamera/0007-imx471-helper.patch'],text=True))
