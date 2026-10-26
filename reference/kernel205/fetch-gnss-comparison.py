"""Read public upstream GNSS sources; never execute or install fetched code."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
import hashlib, json, re, subprocess, os

here = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel205/gnss-related-sources')
out.mkdir(mode=0o700, exist_ok=True)

def fetch(url, name):
    try:
        with urlopen(Request(url, headers={'User-Agent': 'samurai-linux-source-review'}), timeout=35) as response:
            data = response.read(2_000_001)
        assert len(data) <= 2_000_000
        (out / name).write_bytes(data)
        return data
    except Exception as error:
        (out / (name + '.failure.txt')).write_text(type(error).__name__ + ': ' + str(error))
        raise

def repo_sources(repo):
    label = repo.split('/')[0]
    # The unauthenticated GitHub API returned 403. Preserve those receipts and
    # use Git's public read-only protocol, with no checkout, hooks or submodules.
    checkout = out / (label + '-git')
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    def git(*args):
        p = subprocess.run(['git', *args], capture_output=True, env=env, timeout=120)
        if p.returncode:
            (out / (label + '-git-failure.log')).write_bytes(p.stdout + p.stderr)
            raise RuntimeError(label + ' public Git read failed; log retained')
        return p.stdout
    refs = git('ls-remote', '--symref', 'https://github.com/' + repo + '.git', 'HEAD')
    (out / (label + '-refs.txt')).write_bytes(refs)
    branch = re.search(rb'ref: refs/heads/([^\t\n]+)', refs)[1].decode()
    if not checkout.exists():
        git('-c', 'core.hooksPath=/dev/null', 'clone', '--depth=1', '--filter=blob:none', '--no-checkout', '--branch', branch, 'https://github.com/' + repo + '.git', str(checkout))
    commit = git('-C', str(checkout), 'rev-parse', 'HEAD').decode().strip()
    paths = git('-C', str(checkout), 'ls-tree', '-r', '--name-only', commit).decode().splitlines()
    relevant = [p for p in paths if re.search(r'gps|gnss|izat|loc_launcher|xtra', p, re.I)]
    additional = ['README.md', 'BoardConfig.mk', 'device.mk', 'proprietary-files.txt', 'vendor.prop', 'system_ext.prop']
    selected = sorted(set(relevant + [p for p in additional if p in paths]))
    selected = [p for p in selected if not re.search(r'\.(so|bin|apk|png|jpg|zip)$', p)]
    assert len(selected) <= 35
    files = {}
    for path in selected:
        url = 'https://raw.githubusercontent.com/' + repo + '/' + commit + '/' + path
        data = git('-C', str(checkout), 'show', commit + ':' + path)
        assert len(data) <= 2_000_000
        (out / (label + '-' + path.replace('/', '__'))).write_bytes(data)
        files[path] = dict(url=url, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
    # Findings contain public source lines only, not handset/private configuration.
    findings = []
    for path in selected:
        text = (out / (label + '-' + path.replace('/', '__'))).read_text(errors='replace')
        for number, line in enumerate(text.splitlines(), 1):
            if re.search(r'gnss_multiband|gnss|gps|izat|loc_launcher|xtra|SUPL|LPP_PROFILE', line, re.I):
                findings.append(dict(path=path, line=number, text=line[:300]))
    (out / (label + '-findings.json')).write_text(json.dumps(findings, indent=2) + '\n')
    return dict(repo=repo, branch=branch, commit=commit, files=files, relevant_paths=relevant, finding_count=len(findings))

repos = ['HyperTeam/android_device_realme_samurai', 'LineageOS/android_device_oneplus_sm8150-common', 'rapperskull/realme_gps_l5_enabler']
with ThreadPoolExecutor(max_workers=3) as pool:
    results = list(pool.map(repo_sources, repos))
report = dict(stage=205, source_review_only=True, remote_code_executed=False, handset_modified=False, repositories=results)
(here / 'gnss-related-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(repositories=[dict(repo=r['repo'], commit=r['commit'], files=len(r['files']), relevant_paths=r['relevant_paths'], finding_count=r['finding_count']) for r in results], source_review_only=True)))
