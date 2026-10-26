from pathlib import Path
import sys
root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
for request in sys.argv[1:]:
    name, start, end = request.rsplit(':', 2)
    lines = (root / name).read_text().splitlines()
    print(name)
    for index in range(int(start) - 1, min(int(end), len(lines))):
        print(f'{index + 1}: {lines[index]}')
