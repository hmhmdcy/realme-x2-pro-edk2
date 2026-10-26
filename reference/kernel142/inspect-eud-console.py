from pathlib import Path
import re
import tarfile

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
for path in [root/'drivers/tty/serial/eud.c',root/'drivers/tty/serial/eud_earlycon.c']:
    print(str(path.relative_to(root)))
    if path.suffix == '.c':
        for number, line in enumerate(path.read_text().splitlines(),1):
            if (path.name == 'eud.c' and (238 <= number <= 315 or 438 <= number <= 487)) or (path.name == 'eud_earlycon.c' and 55 <= number <= 104):
                print(f'{number}: {line}')
out = Path('/mnt/e/edk2-samurai-out/kernel142')
with tarfile.open(out/'first-runtime-private.tar.gz') as archive:
    text = archive.extractfile('./dmesg.txt').read().decode(errors='replace')
    for line in text.splitlines():
        match = re.match(r'\[\s*(\d+\.\d+)\]',line)
        if ('console' in line.lower() and 'command line' not in line.lower()) or (match and 46.5 <= float(match[1]) <= 47.1):
            print(re.sub(r'0x[0-9a-fA-F]+|\b[0-9a-fA-F]{12,16}\b', '[address]', line))
