#!/usr/bin/env python3
"""One private, pinned schema-tool environment. No kernel build or device access."""
import sys
sys.dont_write_bytecode = True
import email, hashlib, json, pathlib, shutil, subprocess, urllib.request, venv, zipfile

OUT = pathlib.Path('/home/cy122/charging-management-20261023/dwc-flat-schema-check-01')
DS_SHA = 'defcbe1be176dec69c65b9700c9cd992cba3b409976a1404b9c0b5080aa5f4c1'
FDT_SHA = 'e9503d70f92a202c5c2df6b618694c93893d17ec34ef71141a0da187344c0d99'
FDT_SOURCE_SHA = 'b23d03d10ab62ad1f4e7eedde0eb8a7a8872cc08d2a5c2bba7b48bb6fd3c69f4'
CACHE = pathlib.Path('/root/.cache/pip/wheels/20/0a/cc/8a5d2391fbd6dc34cdf7e5eee2f5680b3e7f75279e6a85da67/pylibfdt-1.7.2.post2-cp314-cp314-linux_x86_64.whl')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, obj):
    (OUT/name).write_text(json.dumps(obj, indent=2) + '\n')

def run(name, argv):
    with (OUT/(name+'.stdout')).open('wb') as out, (OUT/(name+'.stderr')).open('wb') as err:
        p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
        print(name, 'pid', p.pid, flush=True)
        rc = p.wait()
    receipt = {'argv': argv, 'pid': p.pid, 'wait_returncode': rc,
               'stdout_sha256': sha(OUT/(name+'.stdout')), 'stderr_sha256': sha(OUT/(name+'.stderr'))}
    save(name+'-process.json', receipt)
    if rc:
        raise RuntimeError(name+' failed: '+str(rc))

def main():
    if OUT.exists():
        raise RuntimeError('Unique private directory already exists; do not replay')
    assert sha(CACHE) == FDT_SHA
    origin = json.loads((CACHE.parent/'origin.json').read_text())
    assert origin['archive_info']['hashes']['sha256'] == FDT_SOURCE_SHA
    assert origin['url'].startswith('https://files.pythonhosted.org/')
    OUT.mkdir()
    save('cached-pylibfdt-origin.json', {'path':str(CACHE), 'wheel_sha256':FDT_SHA, 'origin':origin})
    metadata = json.load(urllib.request.urlopen('https://pypi.org/pypi/dtschema/2026.9/json', timeout=30))
    save('pypi-dtschema-2026.9.json', metadata)
    wheel = next(x for x in metadata['urls'] if x['filename']=='dtschema-2026.9-py3-none-any.whl')
    assert wheel['digests']['sha256'] == DS_SHA
    assert wheel['url'].startswith('https://files.pythonhosted.org/')
    downloaded = OUT/wheel['filename']
    with urllib.request.urlopen(wheel['url'], timeout=30) as response, downloaded.open('wb') as output:
        shutil.copyfileobj(response, output)
    assert sha(downloaded) == DS_SHA
    venv.EnvBuilder(with_pip=True).create(OUT/'venv')
    py = str(OUT/'venv/bin/python')
    wheels = OUT/'wheels'
    wheels.mkdir()
    run('download', [py, '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check', 'download',
        '--no-cache-dir', '--timeout', '30', '--retries', '1', '--index-url', 'https://pypi.org/simple',
        '--only-binary=:all:', '--dest', str(wheels), str(downloaded), str(CACHE)])
    lock = []
    packages = []
    for path in sorted(wheels.glob('*.whl')):
        with zipfile.ZipFile(path) as archive:
            entry = next(n for n in archive.namelist() if n.endswith('.dist-info/METADATA'))
            meta = email.message_from_bytes(archive.read(entry))
        digest = sha(path)
        lock.append(f"{meta['Name']}=={meta['Version']} --hash=sha256:{digest}")
        packages.append({'name':meta['Name'], 'version':meta['Version'], 'filename':path.name, 'sha256':digest})
    (OUT/'requirements.lock').write_text('\n'.join(lock)+'\n')
    save('wheel-pins.json', packages)
    run('install', [py, '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check', 'install',
        '--no-cache-dir', '--no-index', '--find-links', str(wheels), '--require-hashes',
        '--report', str(OUT/'install-report.json'), '-r', str(OUT/'requirements.lock')])
    run('validate-help', [str(OUT/'venv/bin/dt-validate'), '--help'])
    save('setup-result.json', {'passed':True, 'private_directory':str(OUT), 'python':sys.version,
        'dtschema_version':'2026.9', 'pylibfdt_version':'1.7.2.post2', 'packages':packages,
        'system_python_unchanged':True, 'scope':'private venv only; no schema validation yet'})
    print('SETUP_PASSED', str(OUT), flush=True)

if __name__ == '__main__':
    main()
