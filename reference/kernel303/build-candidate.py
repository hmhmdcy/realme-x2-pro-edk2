"""Build only the isolated IPA/pipeline candidate in the preserved SDK."""
from pathlib import Path
import hashlib, json, os, shutil, signal, subprocess, sys
import host
HERE = Path(__file__).resolve().parent
SDK = Path('/home/cy122/x2pro-linux/libcamera214-root')
tree = SDK / 'work/libcamera299-inline'
assert (HERE / 'baseline-preservation-validation.json').exists()
sources = {'include/libcamera/ipa/camss.mojom': HERE / 'camss.mojom'}
for directory, target in [('ipa', 'src/ipa/camss-vfe'), ('pipeline', 'src/libcamera/pipeline/camss-vfe')]:
    for source in (HERE / directory).glob('*'):
        sources[target + '/' + source.name] = source
for name, source in sources.items():
    if not (tree / name).exists() or source.read_bytes() != (tree / name).read_bytes():
        shutil.copyfile(source, tree / name)
attempt = 1
while (host.PRIVATE / f'build-r{attempt}-private.log').exists():
    attempt += 1
proc = subprocess.Popen(['chroot', str(SDK), '/usr/bin/ninja', '-C', '/work/libcamera299-inline/output', '-j8'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
try:
    out, err = proc.communicate(timeout=1200)
except subprocess.TimeoutExpired:
    os.killpg(proc.pid, signal.SIGTERM)
    out, err = proc.communicate(timeout=20)
(host.PRIVATE / f'build-r{attempt}-private.log').write_bytes(out + err)
print((out + err).decode()[-6500:])
report = dict(stage=303, attempt=attempt, build_exit=proc.returncode, not_installed=True,
              hardware_verified=False, sensor_mode='imx319 1632x1224 only',
              source_sha256={n: hashlib.sha256((tree / n).read_bytes()).hexdigest() for n in sources})
(HERE / 'build-validation.json').write_text(json.dumps(report, indent=2) + '\n')
sys.exit(proc.returncode)
