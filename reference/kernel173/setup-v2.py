from pathlib import Path
import hashlib, json, os, shutil, subprocess

os.umask(0o077)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == Path('/var/lib/samurai/k173-source/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#172 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
files = Path('/tmp/k173-candidate-v2-files')
manifest = json.loads((files / 'manifest.json').read_text())['sha256']
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,digest in manifest.items(): assert sha(files/n)==digest
assert sha(Path('/usr/libexec/samurai-audio-route')) == manifest['samurai-audio-route.py']
candidate = Path('/run/samurai-ucm173-v2'); assert not candidate.exists()
shutil.copytree('/usr/share/alsa/ucm2',candidate); candidate.chmod(0o755)
for n in ['HiFi.conf','Realme_X2_Pro.conf']:
    dest = candidate / 'conf.d/Realme_X2_Pro' / n
    shutil.copyfile(files/n,dest); dest.chmod(0o644)
    shutil.copyfile(files/n,Path('/tmp/k173-candidate-files')/n)
shutil.copyfile(files/'manifest.json','/tmp/k173-candidate-files/manifest.json')
print('K173_V2_SANDBOX_READY',flush=True)
