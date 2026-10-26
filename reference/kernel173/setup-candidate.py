from pathlib import Path
import hashlib, json, os, shutil, subprocess

os.umask(0o077)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k173-source/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#172 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
files = Path('/tmp/k173-candidate-files')
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((files / 'manifest.json').read_text())
for n,digest in manifest['sha256'].items(): assert sha(files / n) == digest,n
helper = Path('/usr/libexec/samurai-audio-route'); assert not helper.exists()
if not helper.parent.exists():
    helper.parent.mkdir(parents=True,mode=0o755); helper.parent.chmod(0o755)
shutil.copyfile(files / 'samurai-audio-route.py',helper); helper.chmod(0o755)
candidate = Path('/run/samurai-ucm173'); assert not candidate.exists()
shutil.copytree('/usr/share/alsa/ucm2',candidate); candidate.chmod(0o755)
for n in ['Realme_X2_Pro.conf','HiFi.conf']:
    dest = candidate / 'conf.d/Realme_X2_Pro' / n
    shutil.copyfile(files / n,dest); dest.chmod(0o644)
out = Path('/var/lib/samurai/k173-setup'); out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
env = os.environ.copy(); env['ALSA_CONFIG_UCM2'] = str(candidate)
p = subprocess.run(['alsaucm','-c','hw:Pro','list','_verbs'],env=env,capture_output=True)
(out / 'parse-private.log').write_bytes(p.stdout+p.stderr)
assert p.returncode == 0 and b'HiFi' in p.stdout, (p.returncode,p.stderr.decode())
baseline = json.loads(Path('/var/lib/samurai/k173-source/validation.json').read_text())
for n,digest in baseline['ucm132_before_sha256'].items():
    assert sha(Path('/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro') / n) == digest
report = dict(stage=173,kernel_build=172,helper_sha256=sha(helper),candidate_ucm_parse_pass=True,
              installed_ucm132_still_unchanged=True,sha256=manifest['sha256'])
(out / 'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
