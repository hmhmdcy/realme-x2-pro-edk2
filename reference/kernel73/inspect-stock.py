from pathlib import Path
import gzip, hashlib, json, re, struct, tarfile

root = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel73')
old = Path('/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z')
out = Path('/mnt/e/edk2-samurai-out/kernel73')
raw = gzip.decompress((out/'before-dmesg.gz').read_bytes())
assert hashlib.sha256(raw).hexdigest() == '28f9c085c4a47c8623e3aa503121ea596acfda7a801e12740e418a6eb6a333fd'
(root/'before-dmesg.txt').write_bytes(raw)
with tarfile.open(old/'live-device-tree.tar') as tar:
    files = {m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
phandles = {struct.unpack('>I', b)[0]: n.rsplit('/',1)[0] for n,b in files.items()
            if n.endswith('/phandle') and len(b) == 4}
report = {}
for n,b in files.items():
    if ('sofef03f' in n or n.startswith('./soc/dsi_panel_pwr_supply/') or
            n.startswith('./soc/qcom,dsi-display-primary/')):
        key = n.rsplit('/',1)[-1]
        if key in ('qcom,mdss-dsi-on-command', 'qcom,mdss-dsi-off-command'):
            (root/(('live60-on.bin' if key.endswith('on-command') else 'live60-off.bin')
                   if '/timing@0/' in n else ('live90-on.bin' if key.endswith('on-command') else 'live90-off.bin'))).write_bytes(b)
            continue
        if len(b) and b[-1] == 0 and all(c in (9,10,13) or 32<=c<127 for c in b.rstrip(b'\0')):
            value = b.decode().rstrip('\0')
        elif len(b) % 4 == 0 and len(b) <= 128:
            cells = struct.unpack('>'+'I'*(len(b)//4), b)
            value = {'cells': cells}
            if cells and (key.endswith(('-supply','-gpio')) or key in
                    ('qcom,panel-supply-entries', 'qcom,dsi-panel', 'pinctrl-0', 'pinctrl-1')):
                value['controller'] = phandles.get(cells[0])
        else:
            value = b.hex(' ')
        report[n] = value
(root/'live-display-properties.json').write_text(json.dumps(report, indent=2)+'\n')
print('Saved', len(report), 'display properties; selected panel:',
      {n:v for n,v in report.items() if n.endswith('qcom,dsi-panel')})
