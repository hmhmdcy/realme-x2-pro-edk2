"""Archive audited evidence and mirror only this session's documentation."""
from pathlib import Path
import hashlib, json, shutil, subprocess

out = Path('/mnt/e/edk2-samurai-out/kernel70')
win = Path('/mnt/e/RealmeX2Pro edk2')
repo = Path('/home/cy122/edk2-samurai/repo')
prefix = 'Platform/Realme/sm8150/'
baseline = '218812bca7dacd7aaec7cd1aae74bec449433df4'
docs = ['HANDOVER-NEXT.md', 'README.md', 'RX-CONSOLE.md', 'FLYWHEEL.md',
        'linux-port/README.md', 'DOCS-INDEX.md', 'linux-port/docs/00-INDEX.md',
        'linux-port/docs/ROOTFS-PRESERVE-ANDROID.md',
        'sessions/70-pm8009-resource-and-touch-prerequisites.md']
assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD']).decode().strip() == baseline
assert not subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'])
refs = win / 'reference/kernel70'
assert {p.name for p in refs.iterdir()} == {'README.md'}
for source in sorted(out.iterdir()):
    if source.is_file() and source.suffix in ('.raw', '.txt', '.gz', '.json', '.py', '.ps1'):
        shutil.copyfile(source, refs / source.name)
for name in docs + ['reference/kernel70/' + p.name for p in refs.iterdir() if p.is_file()]:
    target = repo / prefix / name
    assert target.resolve().is_relative_to(repo.resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(win / name, target)
subprocess.run(['git', '-C', str(repo), 'diff', '--check', '--', *[prefix + n for n in docs]], check=True)
run = subprocess.run(['bash', str(win / 'linux-port/scripts/docs-health-check.sh')], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(out / 'docs-health-check.txt').write_bytes(run.stdout)
assert run.returncode == 0 and b'RESULT: clean' in run.stdout, run.stdout.decode()
shutil.copyfile(out / 'docs-health-check.txt', refs / 'docs-health-check.txt')
manifest = [hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name
            for p in sorted(refs.iterdir()) if p.is_file() and p.name != 'SHA256SUMS']
(refs / 'SHA256SUMS').write_text('\n'.join(manifest) + '\n')
for name in ('docs-health-check.txt', 'SHA256SUMS'):
    shutil.copyfile(refs / name, repo / prefix / 'reference/kernel70' / name)
subprocess.run(['python3', str(refs / 'verify.py')], check=True, stdout=subprocess.DEVNULL)
print('Docs health clean; authored whitespace and strict evidence manifest verified.')
print('Curated documents:', len(docs), '; reference files:', len(list(refs.iterdir())))
