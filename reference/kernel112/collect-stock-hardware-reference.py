from pathlib import Path
import hashlib, json, subprocess

repo = Path('/home/cy122/x2pro-linux/refs/realme-x2pro-androidr-project-k112')
out = Path('/mnt/e/edk2-samurai-out/kernel112/stock-hardware-reference')
assert not out.exists(); out.mkdir()
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
assert commit == '23172a1571bd91156032cc9fef16284a82b63d2c'
files = ['arch/arm64/boot/dts/19781/' + n for n in
         ['sm8150.dtsi', 'sm8150-mtp.dtsi', 'sm8150-mtp-overlay.dts',
          'sm8150-regulator.dtsi', 'sm8150-slpi-pinctrl.dtsi']]
files += ['drivers/clk/qcom/scc-sm8150.c']
hashes = {}
for name in files:
    with (out / 'fetch-errors-private.txt').open('ab') as err:
        data = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=repo, stderr=err)
    (out / Path(name).name).write_bytes(data)
    hashes[name] = hashlib.sha256(data).hexdigest()
(out / 'sources.json').write_text(json.dumps(dict(commit=commit, hashes=hashes), indent=2)+'\n')
print('Matching official board DTS and SCC driver reference captured privately')
