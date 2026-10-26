from pathlib import Path
import hashlib, json, os, subprocess

os.umask(0o077)
repo = Path('/home/cy122/x2pro-linux/refs/realme-amp-git-k102')
commit = '9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
out = Path('/mnt/e/edk2-samurai-out/kernel171')
out.mkdir(mode=0o700, exist_ok=True)
tree = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit, 'audio-kernel',
                               'arch/arm64/boot/dts/19781/sm8150-oppo-audio-overlay.dtsi',
                               'arch/arm64/boot/dts/19781/sm8150-pinctrl.dtsi'], cwd=repo, text=True).splitlines()
paths = [p for p in tree if p.startswith('audio-kernel/asoc/codecs/') and ('934' in p or 'tavil' in p)]
print(json.dumps(dict(codec_source_paths=paths)), flush=True)
selected = ['audio-kernel/asoc/msm-dai-q6-v2.c', 'audio-kernel/asoc/msm-dai-q6-v2.h', 'audio-kernel/include/dsp/q6afe-v2.h',
            'arch/arm64/boot/dts/19781/sm8150-oppo-audio-overlay.dtsi', 'arch/arm64/boot/dts/19781/sm8150-pinctrl.dtsi']
selected += [p for p in paths if p.endswith('.c') or p.endswith('.h')]
records = []
for p in selected:
    if p not in tree:
        continue
    result = subprocess.run(['git', 'show', commit + ':' + p], cwd=repo, capture_output=True)
    assert result.returncode == 0, (p, result.stderr.decode(errors='replace'))
    target = out / p
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(result.stdout)
    records.append(dict(path=p, bytes=len(result.stdout), sha256=hashlib.sha256(result.stdout).hexdigest()))
report = dict(stage=171, primary_repository='https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source',
              pinned_commit=commit, files=records, source_or_device_not_modified=True)
(out / 'oem-contract-provenance.json').write_text(json.dumps(report, indent=2) + '\n')
Path(__file__).with_name('oem-contract-provenance.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(files=len(records))), flush=True)
