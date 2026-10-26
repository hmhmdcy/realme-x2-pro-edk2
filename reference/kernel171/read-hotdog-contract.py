from pathlib import Path
import hashlib, json, os, subprocess

os.umask(0o077)
url = 'https://github.com/Sr-0w/hotdog-linux-bringup.git'
dest = Path('/home/cy122/x2pro-linux/refs/hotdog-audio-k171')
out = Path('/mnt/e/edk2-samurai-out/kernel171/hotdog-reference')
assert not dest.exists()
out.mkdir(parents=True, mode=0o700)
commit = subprocess.check_output(['git', 'ls-remote', url, 'HEAD'], text=True).split()[0]
assert len(commit) == 40 and all(c in '0123456789abcdef' for c in commit)
subprocess.run(['git', 'init', '-q', str(dest)], check=True)
subprocess.run(['git', 'remote', 'add', 'origin', url], cwd=dest, check=True)
with (out / 'fetch-private.log').open('wb') as log:
    subprocess.run(['git', 'fetch', '--depth=1', '--filter=blob:none', 'origin', commit], cwd=dest,
                   stdout=log, stderr=subprocess.STDOUT, check=True)
tree = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit], cwd=dest, text=True).splitlines()
selected = [p for p in tree if any(s in p.lower() for s in ['audio', 'tfa9874', 'wcd934'])]
print(json.dumps(dict(commit=commit, audio_paths=selected)), flush=True)
records = []
for p in selected:
    if p.endswith(('.patch', '.md', '.conf', '.c', '.h', '.dts', '.dtsi', '.py', '.sh')):
        result = subprocess.run(['git', 'show', commit + ':' + p], cwd=dest, capture_output=True)
        assert result.returncode == 0, (p, result.stderr.decode(errors='replace'))
        target = out / p
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(result.stdout)
        records.append(dict(path=p, bytes=len(result.stdout), sha256=hashlib.sha256(result.stdout).hexdigest()))
report = dict(stage=171, primary_repository=url.removesuffix('.git'), pinned_commit=commit, files=records,
              read_only_reference=True, external_scripts_not_executed=True)
for directory in [out, Path(__file__).parent]:
    (directory / 'hotdog-contract-provenance.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(downloaded_files=len(records))), flush=True)
