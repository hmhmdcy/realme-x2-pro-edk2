"""Pin existing author repositories and inspect actual source, not search summaries."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel279/existing-solutions')
PRIVATE.mkdir(exist_ok=True)
HEADERS = {'User-Agent': 'Samurai-CAMSS-source-audit', 'Accept': 'application/vnd.github+json'}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=35) as reply:
        return reply.read(16 * 1024 * 1024)


def inspect(spec):
    repo, branch, paths = spec
    result = dict(repo=repo, requested_ref=branch, files={})
    try:
        commit = json.loads(get('https://api.github.com/repos/' + repo + '/commits/' +
                               urllib.parse.quote(branch, safe='')))
        pin = commit['sha']
        result.update(commit=pin, date=commit['commit']['committer']['date'],
                      subject=commit['commit']['message'].splitlines()[0])
        for name in paths:
            url = f'https://raw.githubusercontent.com/{repo}/{pin}/{name}'
            try:
                data = get(url)
                local = PRIVATE / (repo.replace('/', '_') + '--' + name.replace('/', '__'))
                local.write_bytes(data)
                text = data.decode(errors='replace')
                terms = ['OPE', 'ope', 'CamssIsp', 'VFE', 'software', 'params', 'stats',
                         'sm8150', 'autofocus', 'millicam']
                hits = [f'{i + 1}: {line}' for i, line in enumerate(text.splitlines())
                        if any(term in line for term in terms)]
                result['files'][name] = dict(url=url, sha256=hashlib.sha256(data).hexdigest(),
                                            bytes=len(data), local_name=local.name)
                result.setdefault('source_excerpts', {})[name] = hits[:18]
            except Exception as error:
                result['files'][name] = dict(url=url, error=str(error))
    except Exception as error:
        result['error'] = str(error)
    return result


specs = [
    ('jwrdegoede/libcamera', 'camss_pipeline_v2.1', [
        'src/libcamera/pipeline/camss/camss.cpp',
        'src/libcamera/pipeline/camss/camss_isp.h',
        'src/libcamera/pipeline/camss/camss_isp_ope.cpp',
        'src/ipa/camss/ipa_context.h']),
    ('loicpoulain/camss-isp-m2m-test', 'HEAD', ['README.md']),
    ('loicpoulain/linux', 'camss-isp-dev', [
        'drivers/media/platform/qcom/camss/isp/ope/ope_core.c']),
    ('Sr-0w/hotdog-linux-bringup', 'main', [
        'docs/evidence/2026-08-10-mainline616-camera-autofocus.md', 'README.md']),
    ('0xB0D/ife-tests', 'master', ['test-pix.sh', 'test-stats.sh', 'test-params.sh']),
]
with ThreadPoolExecutor(max_workers=4) as pool:
    rows = list(pool.map(inspect, specs))
(PRIVATE / 'source-excerpts-private.json').write_text(json.dumps(rows, indent=2) + '\n')
for row in rows:
    print(row['repo'], row.get('commit', row.get('error')))
    for name, value in row.get('source_excerpts', {}).items():
        print(name, '\n' + '\n'.join(value[:7]))
public = [{key: value for key, value in row.items() if key != 'source_excerpts'} for row in rows]
(ROOT / 'existing-solutions-validation.json').write_text(json.dumps(dict(
    stage=279, repositories=public, sources_not_executed=True, phone_unchanged=True), indent=2) + '\n')
