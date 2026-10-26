from pathlib import Path
import hashlib, json, subprocess, urllib.error, urllib.request

out=Path('/mnt/e/edk2-samurai-out/kernel113/ulog-reference')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
out.mkdir(mode=0o700, exist_ok=True)
repo='Sr-0w/hotdog-linux-bringup'
file='helpers/slpi-ulog-coredump.py'
api=f'https://api.github.com/repos/{repo}/commits?path={file}&per_page=1'
request=urllib.request.Request(api, headers={'User-Agent':'samurai-linux-port'})
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        commit=json.load(response)[0]['sha']
except urllib.error.HTTPError as error:
    if error.code != 403: raise
    lines=subprocess.check_output(['git','ls-remote',f'https://github.com/{repo}.git','refs/heads/main'], timeout=45).decode().splitlines()
    assert len(lines)==1
    commit=lines[0].split()[0]
assert len(commit)==40 and all(c in '0123456789abcdef' for c in commit)
url=f'https://raw.githubusercontent.com/{repo}/{commit}/{file}'
with urllib.request.urlopen(url, timeout=30) as response:
    source=response.read(128*1024)
assert len(source)<128*1024
compile(source, file, 'exec')
dest=out/'slpi-ulog-coredump.py'
dest.write_bytes(source)
report=dict(source=url, commit=commit, sha256=hashlib.sha256(source).hexdigest(),
            bytes=len(source), use='read-only host parser; no firmware/calibration imported',
            relocation_policy='derive from this phone dump and matching firmware; no hotdog defaults accepted')
(ref/'ulog-parser-reference.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
