from pathlib import Path
import json, re, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel160')
with tarfile.open(out / 'first-evidence-private.tar.gz') as archive:
    log = archive.extractfile('k160-first-runtime/dmesg-private.txt').read().decode()
selected = []
for line in log.splitlines():
    stamp = re.match(r'\[\s*(\d+\.\d+)\]', line)
    if stamp and float(stamp[1]) <= 14.5 and any(word in line.lower() for word in
            ['smmu', 'iommu', 'efi:', 'simple', 'clock', 'regulator', 'pinctrl', 'mdss', 'display', 'fbcon', 'scm', 'interconnect', 'gpiod']):
        selected.append(line)
(out / 'early-init-timeline-private.txt').write_text('\n'.join(selected) + '\n')
print('\n'.join(selected))
