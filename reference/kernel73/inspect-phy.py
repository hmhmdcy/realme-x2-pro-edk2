from pathlib import Path
import tarfile, struct, json
old = Path('/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z')
with tarfile.open(old/'live-device-tree.tar') as tar:
    files = {m.name:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
ph = {struct.unpack('>I',b)[0]:n.rsplit('/',1)[0] for n,b in files.items() if n.endswith('/phandle') and len(b)==4}
selected = {n:b.hex(' ') for n,b in files.items() if ('dsi-ctrl' in n or 'dsi-phy' in n) and
    n.endswith(('-supply', 'qcom,ctrl-supply-entries', 'qcom,phy-supply-entries', 'reg'))}
for n,b in files.items():
    if ('dsi_ctrl' in n or 'dsi_phy' in n or 'mdss_dsi0' in n) and n.endswith(('-supply','-supply-entries')):
        selected[n] = b.hex(' ')
for n,h in list(selected.items()):
    b = bytes.fromhex(h)
    if len(b)==4:
        ref = ph.get(struct.unpack('>I',b)[0])
        selected[n] = {'hex':h,'node':ref}
        if ref:
            for sub,raw in files.items():
                if sub.startswith(ref+'/'):
                    selected[sub] = raw.hex(' ')
print(json.dumps(selected,indent=2))
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel73/live-phy-supplies.json').write_text(json.dumps(selected,indent=2)+'\n')
