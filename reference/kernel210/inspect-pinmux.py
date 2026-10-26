from pathlib import Path
import json
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k210-baseline/boot-id-private.txt').read_bytes()
for p in Path('/sys/kernel/debug/pinctrl').glob('*3100000*/pinmux-pins'):
    print(json.dumps(dict(lines=[l for l in p.read_text().splitlines() if any(l.startswith('pin '+str(n)+' ') for n in [12,15,29])],gpio_claims=[l for l in Path('/sys/kernel/debug/gpio').read_text().splitlines() if any(x in l for x in ['gpio-12 ','gpio-15 ','gpio-29 '])])))
