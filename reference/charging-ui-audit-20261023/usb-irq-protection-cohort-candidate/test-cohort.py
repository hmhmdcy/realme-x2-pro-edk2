"""Small offline package boundaries, executing the actual cohort functions."""
from pathlib import Path
import copy
import gzip
import hashlib
import importlib.util
import io
import json
import tarfile
import tempfile
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('actual_offline_cohort', HERE / 'cohort.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
cases = []

def require(value):
    if not value:
        raise AssertionError('test condition')

def rejected(callback):
    try:
        callback()
    except (ValueError, FileExistsError):
        return
    raise AssertionError('expected rejection')

old_raw = (m.PRIVATE / 'r8-candidate/manifest.json').read_bytes()
require(m.sha(old_raw) == '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f')
old = json.loads(old_raw)
hashes = {name: hashlib.sha256(name.encode()).hexdigest() for name in m.CHANGED}
revision = 'usb-irq-protection-observer-01'
new = m.make_manifest(old, hashes, revision)
m.check_manifest_delta(old, new, hashes, revision)
require({p for p in old['installed_files'] if old['installed_files'][p] != new['installed_files'][p]} ==
        {old['modules'][name]['target'] for name in m.CHANGED})
require(old['modules']['samurai-mp2650'] == new['modules']['samurai-mp2650'])
cases.append('actual manifest delta only two module hashes and independent revision')

mutations = [('cap', lambda n: n.update(default_charge_cap_ua=900000)),
             ('source budget', lambda n: n.update(source_budget_enforced=False)),
             ('service', lambda n: n['installed_files'].update({'/usr/sbin/samurai-charging': '0' * 64})),
             ('charger', lambda n: n['modules']['samurai-mp2650'].update(sha256='0' * 64)),
             ('module target', lambda n: n['modules']['samurai-usb-input'].update(target='/tmp/new.ko'))]
for label, mutation in mutations:
    altered = copy.deepcopy(new)
    mutation(altered)
    rejected(lambda: m.check_manifest_delta(old, altered, hashes, revision))
cases.append('forbidden cap/source/service/charger/path changes rejected')

files = {old['modules'][name]['target']: ('synthetic offline ' + name).encode() for name in m.CHANGED}
files[m.MANIFEST] = m.encode(new)
payload = m.archive(files)
require(payload == m.archive(files))
m.check_archive(payload, files)
cases.append('actual deterministic gzip/tar three-file round trip')

def altered_tar(extra=False, duplicate=False, symlink=False):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode='w', format=tarfile.USTAR_FORMAT) as tar:
        for index, (name, content) in enumerate(sorted(files.items())):
            info = tarfile.TarInfo(name.lstrip('/'))
            info.uid = info.gid = 0
            info.uname = info.gname = 'root'
            info.mode = 0o600
            info.size = len(content)
            if symlink and index == 0:
                info.type = tarfile.SYMTYPE
                info.linkname = '/tmp/not-a-module'
                info.size = 0
                tar.addfile(info)
            else:
                tar.addfile(info, io.BytesIO(content))
            if duplicate and index == 0:
                tar.addfile(info, io.BytesIO(content))
        if extra:
            info = tarfile.TarInfo('usr/sbin/unrequested-analyzer')
            info.mode = 0o600
            tar.addfile(info, io.BytesIO())
    return gzip.compress(raw.getvalue(), mtime=0)

for kwargs in ({'extra': True}, {'duplicate': True}, {'symlink': True}):
    rejected(lambda: m.check_archive(altered_tar(**kwargs), files))
altered_files = dict(files)
first = next(iter(altered_files))
altered_files[first] += b' changed'
rejected(lambda: m.check_archive(payload, altered_files))
cases.append('extra/duplicate/symlink/changed-byte archive members rejected')

carriers = {'boot': {'sha256': 'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'},
            'native_DTB': {'sha256': '13d359c4a78ed423d52f1d5e09345c7dc7032811fabe786952ac11e868adee9f'},
            'logdump': {'sha256': 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'},
            'Image502_sha256': '085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955',
            'rollback_boot': {'sha256': '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'}}
m.validate_carriers(carriers)
for key in ['boot', 'native_DTB', 'logdump', 'rollback_boot']:
    altered = copy.deepcopy(carriers)
    altered[key]['sha256'] = '0' * 64
    rejected(lambda: m.validate_carriers(altered))
altered = copy.deepcopy(carriers)
altered['Image502_sha256'] = '0' * 64
rejected(lambda: m.validate_carriers(altered))
cases.append('exact boot/DT/Image502 carrier and original boot rollback pins enforced')

usb = (m.PRIVATE / 'usb-input-irq-board-private-01/samurai-usb-input-irq-private.ko').read_bytes()
identity = m.module_identity(usb, 'samurai-usb-input')
require(identity['sha256'] == '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f')
rejected(lambda: m.module_identity(usb, 'samurai-gauge-protection'))
wrong_arch = bytearray(usb)
wrong_arch[18:20] = b'\x3e\0'
rejected(lambda: m.module_identity(bytes(wrong_arch), 'samurai-usb-input'))
cases.append('actual frozen USB ELF identity accepted; swapped name/architecture rejected')

with tempfile.TemporaryDirectory(prefix='samurai-cohort-targeted-') as temp:
    directory = Path(temp) / 'already-exists'
    directory.mkdir()
    sentinel = directory / 'sentinel'
    sentinel.write_bytes(b'unchanged')
    rejected(lambda: m.materialize(directory, {}, {}, {}))
    require(sentinel.read_bytes() == b'unchanged' and list(directory.iterdir()) == [sentinel])
cases.append('existing output rejected before any write; no replay/overwrite')

result = {'passed': True, 'actual_package_boundary_cases': len(cases), 'cases': cases,
          'tested_files': {'cohort.py': m.file_sha(HERE / 'cohort.py'),
                           'test-cohort.py': m.file_sha(Path(__file__))},
          'frozen_USB_module_sha256': m.sha(usb), 'actual_R8_manifest_sha256': m.sha(old_raw),
          'synthetic_new_module_payloads_are_not_hardware_evidence': True,
          'driver_function_tests_repeated': False, 'compiler_or_device_or_SSH_USB_SDK_Git_used': False}
(HERE / 'test-result.json').write_bytes(m.encode(result))
print(json.dumps({'passed': True, 'actual_package_boundary_cases': len(cases),
                  'receipt_sha256': m.file_sha(HERE / 'test-result.json')}))
