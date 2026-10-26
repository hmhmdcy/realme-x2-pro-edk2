from pathlib import Path
import json
import re

out = Path('/mnt/e/edk2-samurai-out/kernel78')

def parse(path):
    blocks = {}
    current = None
    for line in path.read_text().splitlines():
        heading = re.fullmatch(r'=+([^=]+)=+', line)
        if heading:
            current = heading[1]
            blocks.setdefault(current, {})
            continue
        row = re.fullmatch(r'0x([0-9a-f]+) : ((?:[0-9a-f]{8} ?)+)', line)
        if row and current:
            start = int(row[1], 16)
            for i, word in enumerate(row[2].split()):
                blocks[current][start + 4 * i] = int(word, 16)
    return blocks

base = parse(out / 'healthy-kms.txt')
candidate = parse(out / 'fresh-kms.txt')
diff = []
for block in base:
    changes = []
    for reg, value in base[block].items():
        other = candidate.get(block, {}).get(reg)
        if other is not None and value != other:
            changes.append({'offset': hex(reg), 'healthy': hex(value), 'fresh': hex(other)})
    if changes:
        diff.append({'block': block, 'changes': changes})
(out / 'kms-diff.json').write_text(json.dumps(diff, indent=2) + '\n')
for item in diff:
    print(item['block'], len(item['changes']))
    if item['block'].startswith(('dsi', 'intf', 'ctl', 'pingpong', 'dsc', 'top')):
        for reg in item['changes']:
            print(' ', reg['offset'], 'healthy=' + reg['healthy'], 'fresh=' + reg['fresh'])
