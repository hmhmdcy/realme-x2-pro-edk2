from pathlib import Path
import json
import re
import subprocess

out = Path('/var/lib/samurai/k183-mixer-comparison')
out.mkdir(mode=0o700)
assert __import__('os').uname().version.startswith('#181 ')
now = subprocess.check_output(['amixer', '-c', '0', 'contents'], text=True)
(out / 'current-full-mixer-private.txt').write_text(now)
old = Path('/var/lib/samurai/k181-dmic0-ucm181-low24/mixer-full-before-private.txt').read_text()
def parse(text):
    result = {}
    for section in re.split(r'(?=^numid=)', text, flags=re.M):
        name = re.search(r"name='([^']+)'", section)
        values = re.search(r': values=(.*)', section)
        if name and values:
            result[name[1]] = values[1].strip()
    return result
before, after = parse(old), parse(now)
diff = {name: dict(before=value, current=after.get(name)) for name, value in before.items() if value != after.get(name)}
(out / 'validation.json').write_text(json.dumps(dict(kernel_build=181, control_count=len(after), differences=diff), indent=2) + '\n')
print(json.dumps(dict(control_count=len(after), differences=diff)))
