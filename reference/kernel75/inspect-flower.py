from pathlib import Path
import gzip, json, re, subprocess

root = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel75')
out = Path('/mnt/e/edk2-samurai-out/kernel75')
kernel = Path('/home/cy122/x2pro-linux/linux')

for name in ('flower-dmesg', 'matched-boot-dmesg', 'mixed-tests', 'flower-kms'):
    p = out / (name + '.gz')
    if not p.exists():
        continue
    data = gzip.decompress(p.read_bytes())
    (out / (name + '.txt')).write_bytes(data)
    if name.endswith('dmesg'):
        lines = data.decode().splitlines()
        relevant = [line for line in lines if re.search(r'GPU|Adreno|gmu|zap|firmware|DSC|frame stalled|CTL|stalled INTF|SMMU|fault|Underflow', line, re.I)]
        print(name, '\n' + '\n'.join(relevant[:70]))
    if name == 'flower-kms':
        sections = re.split(r'(={5,}[^\n]+=+)', data.decode())
        for i in range(1, len(sections), 2):
            if re.search(r'dsc_[01]|pingpong_[01]=|ctl_0|intf_1', sections[i], re.I):
                print(sections[i], sections[i+1][:900])

props = json.loads((root.parent / 'kernel73/live-display-properties.json').read_text())
for key, value in props.items():
    if '/timing@0/' in key and re.search(r'dsc|clk|clock|topology|bpp', key):
        print(key.rsplit('/', 1)[-1], value)

src = (root.parent / 'kernel73/kms-smoke.c').read_text()
assert src.count('    sleep(2);') == 1
src = src.replace('    sleep(2);', '''    unsigned hold = argc > 3 ? (unsigned)atoi(argv[3]) : 120;
    if (hold > 300) hold = 300;
    printf("Holding static pattern %u for %u seconds, then restoring console\\n",pattern,hold);
    fflush(stdout);
    for (i=0;i<hold;i++) {
        if (!access("/tmp/k75-static-release",F_OK)) break;
        sleep(1);
    }''')
(root / 'kms-static.c').write_text(src)
subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-Wall','-Wextra',
    '-D__user=', '-D__EXPORTED_HEADERS__',
    '-I'+str(kernel/'include/uapi'), '-I'+str(kernel/'arch/arm64/include/uapi'),
    '-I'+str(kernel/'arch/arm64/include/generated/uapi'),
    str(root/'kms-static.c'),'-o',str(out/'kms-static')],check=True)
print('Built bounded static-pattern tool')
