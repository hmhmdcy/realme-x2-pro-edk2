"""Offline, exact three-file charging cohort; no device or installer actions."""
from pathlib import Path
import argparse
import copy
import gzip
import hashlib
import io
import json
import os
import struct
import sys
import tarfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('E:/edk2-samurai-out/charging-management-20261023')
OUT = PRIVATE / 'usb-irq-protection-cohort-private-01'
MANIFEST = '/usr/share/samurai-charging/manifest.json'
RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
CHANGED = ('samurai-usb-input', 'samurai-gauge-protection')

def need(value, message):
    if not value:
        raise ValueError(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def encode(data):
    return (json.dumps(data, indent=2) + '\n').encode()

def pinned(entry, *, small=False):
    path = Path(entry['path'])
    need(path.is_file() and not path.is_symlink(), 'missing/indirect input: ' + str(path))
    need(file_sha(path) == entry['sha256'], 'input hash: ' + str(path))
    if 'bytes' in entry:
        need(path.stat().st_size == entry['bytes'], 'input size: ' + str(path))
    if small:
        need(path.stat().st_size < 2_000_000, 'small input bound: ' + str(path))
        return path.read_bytes()
    return path

def module_identity(raw, expected_name):
    need(raw[:6] == b'\x7fELF\x02\x01' and len(raw) >= 64, 'ELF64 little endian')
    need(struct.unpack_from('<HH', raw, 16) == (1, 183), 'AArch64 relocatable module')
    offset = struct.unpack_from('<Q', raw, 40)[0]
    stride, count, strings = struct.unpack_from('<HHH', raw, 58)
    need(stride == 64 and 0 < strings < count and offset + stride * count <= len(raw), 'section table')
    sections = [struct.unpack_from('<IIQQQQIIQQ', raw, offset + i * stride) for i in range(count)]
    def data(section):
        start, size = section[4:6]
        need(start + size <= len(raw), 'section bytes')
        return raw[start:start + size]
    names = data(sections[strings])
    table = {}
    for section in sections:
        need(section[0] < len(names), 'section name')
        name = names[section[0]:].split(b'\0', 1)[0].decode('ascii')
        need(name not in table or name == '', 'duplicate section')
        table[name] = section
    need('.modinfo' in table and '.note.gnu.build-id' in table, 'module identity sections')
    fields = {}
    for field in data(table['.modinfo']).split(b'\0'):
        if b'=' in field:
            key, value = field.decode().split('=', 1)
            fields.setdefault(key, []).append(value)
    need(fields.get('name') == [expected_name.replace('-', '_')], 'module name')
    need(fields.get('intree') == ['Y'], 'in-tree module')
    need(len(fields.get('vermagic', [])) == 1 and
         fields['vermagic'][0] == RELEASE + ' SMP preempt mod_unload aarch64', 'vermagic')
    note = data(table['.note.gnu.build-id'])
    need(len(note) >= 16, 'build-id note')
    namesz, descsz, kind = struct.unpack_from('<III', note)
    aligned = (namesz + 3) & ~3
    need(kind == 3 and namesz == 4 and note[12:16] == b'GNU\0' and
         12 + aligned + ((descsz + 3) & ~3) == len(note) and descsz > 0, 'GNU build-id layout')
    return {'sha256': sha(raw), 'bytes': len(raw), 'name': fields['name'][0],
            'intree': 'Y', 'vermagic': fields['vermagic'][0],
            'resident_note_sha256': sha(note), 'resident_note_hex': note.hex()}

def make_manifest(old, hashes, revision):
    need(set(hashes) == set(CHANGED), 'exactly two replacement modules')
    need(old['release'] == RELEASE and old['adapter_revision'] == 'r8', 'R8 manifest base')
    need(old['default_input_cap_ua'] == 900000 and old['default_charge_cap_ua'] == 250000 and
         old['source_budget_enforced'] is True, 'unchanged policy caps')
    need(set(old['modules']) == set(CHANGED) | {'samurai-mp2650'}, 'three original modules')
    need(revision == 'usb-irq-protection-observer-01', 'independent cohort revision')
    new = copy.deepcopy(old)
    new['adapter_revision'] = revision
    for name in CHANGED:
        target = old['modules'][name]['target']
        need(target == '/lib/modules/' + RELEASE + '/extra/samurai-charging/' + name + '.ko', 'original module path')
        need(old['installed_files'][target] == old['modules'][name]['sha256'], 'base module hash consistency')
        need(hashes[name] != old['modules'][name]['sha256'], 'replacement must be new: ' + name)
        new['modules'][name]['sha256'] = hashes[name]
        new['installed_files'][target] = hashes[name]
    return new

def check_manifest_delta(old, new, hashes, revision):
    need(new == make_manifest(old, hashes, revision), 'manifest has changes outside two hashes/revision')

def archive(files):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as tar:
        for target, raw in sorted(files.items()):
            info = tarfile.TarInfo(target.lstrip('/'))
            info.uid = info.gid = 0
            info.uname = info.gname = 'root'
            info.mode = 0o600
            info.mtime = 0
            info.size = len(raw)
            tar.addfile(info, io.BytesIO(raw))
    compressed = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=compressed, mtime=0) as sink:
        sink.write(stream.getvalue())
    result = compressed.getvalue()
    check_archive(result, files)
    return result

def check_archive(raw, files):
    expected = {name.lstrip('/'): data for name, data in files.items()}
    need(len(expected) == 3 and MANIFEST.lstrip('/') in expected, 'exact three payload files')
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tar:
        members = tar.getmembers()
        need(len(members) == 3 and len({m.name for m in members}) == 3 and
             {m.name for m in members} == set(expected), 'payload member set')
        for member in members:
            need(member.isfile() and member.mode == 0o600 and member.uid == member.gid == 0 and
                 member.uname == member.gname == 'root' and member.mtime == 0 and
                 not member.pax_headers, 'payload type/metadata')
            need(member.size == len(expected[member.name]) and
                 tar.extractfile(member).read() == expected[member.name], 'payload member bytes')

def validate_carriers(carriers):
    need(carriers['boot']['sha256'] == 'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06', 'IRQ boot pair')
    need(carriers['native_DTB']['sha256'] == '13d359c4a78ed423d52f1d5e09345c7dc7032811fabe786952ac11e868adee9f', 'IRQ native DT pair')
    need(carriers['logdump']['sha256'] == 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1', 'Image502 carrier')
    need(carriers['Image502_sha256'] == '085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955', 'Image502 identity')
    need(carriers['rollback_boot']['sha256'] == '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695', 'original boot rollback')

def local_inputs():
    tests = json.loads((HERE / 'test-result.json').read_bytes())
    need(tests['passed'] and tests['actual_package_boundary_cases'] == 7 and
         tests['tested_files']['cohort.py'] == file_sha(Path(__file__)), 'affected package-test binding')
    pins = json.loads((HERE / 'input-pins.json').read_bytes())
    need(pins['schema'] == 'samurai-usb-irq-protection-cohort-inputs-v1', 'input pins schema')
    receipt_bytes = {name: pinned(row, small=True) for name, row in pins['receipts'].items()}
    receipts = {name: json.loads(raw) for name, raw in receipt_bytes.items()}
    usb, protection = receipts['USB_ko'], receipts['protection_ko']
    for name, row in [('USB', usb), ('protection', protection)]:
        need(row['passed'] and row['intree'] == 'Y' and row['release'] == RELEASE and
             row['imports_all_from_Image502_builtin'] and not row['unresolved_strong_imports'] and
             row['actual_config_values_exact_Image502'] and row['generated_autoconf_exact_Image502'], name + ' link/import evidence')
        need(not row['diagnostics'], name + ' link diagnostics')
        need(row['Image502_exports_sha256'] == '84f5fc338ea72a6d71b23da50562f89c7963af50675956d3e0aff30540df4d47' and
             row['config_sha256'] == '23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed', name + ' exact Image502 inputs')
        need(row['commands'] and all(cmd['terminal'] and cmd['returncode'] == 0 for cmd in row['commands']), name + ' command terminal')
    old_raw = pinned(pins['base_manifest'], small=True)
    need(sha(old_raw) == '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f', 'actual R8 manifest')
    old = json.loads(old_raw)
    new_modules = {name: pinned(row, small=True) for name, row in pins['modules'].items()}
    need(set(new_modules) == set(CHANGED), 'two input modules')
    for name, receipt in [('samurai-usb-input', usb), ('samurai-gauge-protection', protection)]:
        need(sha(new_modules[name]) == receipt['module_sha256'] and
             len(new_modules[name]) == receipt['module_bytes'], name + ' actual module binding')
    need(sha(new_modules['samurai-usb-input']) == '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f', 'exact IRQ USB module')
    old_usb = pinned(pins['old_USB'], small=True)
    payload = pinned(pins['old_protection_archive'], small=True)
    target = old['modules']['samurai-gauge-protection']['target'].lstrip('/')
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as tar:
        matches = [member for member in tar.getmembers() if member.name == target]
        need(len(matches) == 1 and matches[0].isfile(), 'retained old protection module')
        old_protection = tar.extractfile(matches[0]).read()
    old_modules = {'samurai-usb-input': old_usb, 'samurai-gauge-protection': old_protection}
    for name, raw in old_modules.items():
        need(sha(raw) == old['modules'][name]['sha256'], 'R8 rollback bytes: ' + name)
    identities = {name: {'old': module_identity(old_modules[name], name),
                         'new': module_identity(new_modules[name], name)} for name in CHANGED}
    need(identities['samurai-gauge-protection']['new']['resident_note_sha256'] ==
         protection['module_note_sha256'], 'actual protection note binding')
    for name in CHANGED:
        need(identities[name]['old']['resident_note_sha256'] != identities[name]['new']['resident_note_sha256'], 'new build-id required: ' + name)
    retained_targets = {'/usr/sbin/samurai-charging', '/etc/init.d/samurai-charging',
                        '/usr/lib/samurai-charging/control-trial.py',
                        '/usr/lib/samurai-charging/live-session.py', '/usr/local/sbin/samurai-usb',
                        old['modules']['samurai-mp2650']['target']}
    need(set(pins['retained']) == retained_targets, 'exact retained source set')
    charger_identity = None
    for target, entry in pins['retained'].items():
        raw = pinned(entry, small=True)
        if target != '/usr/local/sbin/samurai-usb':
            need(sha(raw) == old['installed_files'][target], 'retained R8 file binding: ' + target)
        if target == old['modules']['samurai-mp2650']['target']:
            charger_identity = module_identity(raw, 'samurai-mp2650')
    need(pins['retained']['/usr/local/sbin/samurai-usb']['sha256'] ==
         '2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a', 'startup500 exact retained file')
    validate_carriers(pins['carriers'])
    for key in ['boot', 'native_DTB', 'logdump', 'rollback_boot']:
        pinned(pins['carriers'][key])  # bounded stream hashing, no whole image read
    need(receipts['boot']['passed'] and receipts['boot']['candidate_boot']['sha256'] == pins['carriers']['boot']['sha256'], 'boot passed receipt')
    need(receipts['logdump']['passed'] and receipts['logdump']['candidate']['sha256'] == pins['carriers']['logdump']['sha256'], 'logdump passed receipt')
    need(receipts['DT_pair']['native_DTB']['sha256'] == pins['carriers']['native_DTB']['sha256'] and
         receipts['DT_pair']['USB_module']['sha256'] == sha(new_modules['samurai-usb-input']), 'DT/module paired identity')
    need(receipts['DT_pair']['required_together'] and
         receipts['DT_pair']['new_DTB_must_not_be_used_with_old_R7_module'], 'DT/module inseparability')
    hashes = {name: sha(raw) for name, raw in new_modules.items()}
    new = make_manifest(old, hashes, pins['adapter_revision'])
    check_manifest_delta(old, new, hashes, pins['adapter_revision'])
    new_raw = encode(new)
    forward = {old['modules'][name]['target']: new_modules[name] for name in CHANGED}
    backward = {old['modules'][name]['target']: old_modules[name] for name in CHANGED}
    forward[MANIFEST], backward[MANIFEST] = new_raw, old_raw
    cohort = {
        'schema': 'samurai-usb-irq-protection-offline-cohort-v1', 'cohort_id': pins['cohort_id'],
        'status': 'offline-materialized-not-installed', 'release': RELEASE,
        'old_manifest_sha256': sha(old_raw), 'new_manifest_sha256': sha(new_raw),
        'changed_rootfs_files': sorted(forward), 'modules': identities,
        'unchanged_charger_identity': charger_identity,
        'required_carriers': {k: {f: v for f, v in e.items() if f != 'path'}
                              for k, e in pins['carriers'].items() if isinstance(e, dict)},
        'Image502_sha256': pins['carriers']['Image502_sha256'],
        'retained_files': {target: entry['sha256'] for target, entry in pins['retained'].items()},
        'caps': {'requested_input_ua': 900000, 'requested_charge_ua': 250000,
                 'USB_descriptor_requested_ma': 500, 'source_budget_enforced': True,
                 'native_allowance': 'observed host-authorized power-supply value; not forced by this cohort'},
        'transition': {
            'stage_only_result': 'staged/runtime_pending',
            'resident_notes_before_next_boot': 'old notes above, including USB still referenced by DWC3',
            'old_manager_loaded_matches_new_file_before_reboot_valid': False,
            'new_independent_guard_and_transaction_required': True,
            'prepared_Image502_transaction_reusable': False,
            'module_hot_unload_or_AUTO_issued': False,
            'capture_issued': False,
        },
        'acceptance_pending': ['same native DT/provider probe and both named IRQ registrations',
                               'actual physical IRQ count/event changes with safe budgets/protection',
                               'new protection resident identity and ordinary Health checks',
                               'after matching the new adopted identity, root explicitly starts the already-authorized one-shot evidence capture; never default poll'],
        'receipt_sha256': {name: entry['sha256'] for name, entry in pins['receipts'].items()},
        'not_runtime_permission': True,
    }
    return pins, cohort, forward, backward

def materialize(directory, cohort, forward, backward):
    directory.mkdir(mode=0o700, exist_ok=False)
    report = {'passed': False, 'phase': 'offline-cohort-materialization', 'installed': False,
              'device_or_SSH_USB_SDK_Git_accessed': False, 'output': str(directory),
              'source_sha256': file_sha(Path(__file__)), 'input_pins_sha256': file_sha(HERE / 'input-pins.json')}
    try:
        files = {'manifest.json': forward[MANIFEST], 'rollback-manifest.json': backward[MANIFEST],
                 'cohort.json': encode(cohort), 'usb-irq-protection-payload.tar.gz': archive(forward),
                 'rollback-r8-payload.tar.gz': archive(backward)}
        for name, raw in files.items():
            with (directory / name).open('xb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        check_archive((directory / 'usb-irq-protection-payload.tar.gz').read_bytes(), forward)
        check_archive((directory / 'rollback-r8-payload.tar.gz').read_bytes(), backward)
        report.update(passed=True, cohort_id=cohort['cohort_id'],
                      files={name: {'sha256': file_sha(directory / name), 'bytes': len(raw)}
                             for name, raw in files.items()},
                      changed_files={target: {'sha256': sha(raw), 'bytes': len(raw), 'mode': '0600'}
                                     for target, raw in forward.items()},
                      runtime_validation_pending=True)
    except Exception as error:
        report.update(error=type(error).__name__, message=str(error), replay_permitted=False)
        raise
    finally:
        with (directory / 'result.json').open('xb') as stream:
            stream.write(encode(report))
            stream.flush()
            os.fsync(stream.fileno())
    return report

def audit(directory, cohort, forward, backward):
    report = json.loads((directory / 'result.json').read_bytes())
    need(report['passed'] and report['source_sha256'] == file_sha(Path(__file__)) and
         report['input_pins_sha256'] == file_sha(HERE / 'input-pins.json'), 'materialized result binding')
    for name, entry in report['files'].items():
        need((directory / name).is_file() and not (directory / name).is_symlink() and
             file_sha(directory / name) == entry['sha256'] and
             (directory / name).stat().st_size == entry['bytes'], 'materialized artifact: ' + name)
    need((directory / 'manifest.json').read_bytes() == forward[MANIFEST] and
         (directory / 'rollback-manifest.json').read_bytes() == backward[MANIFEST] and
         json.loads((directory / 'cohort.json').read_bytes()) == cohort, 'materialized exact identities')
    check_archive((directory / 'usb-irq-protection-payload.tar.gz').read_bytes(), forward)
    check_archive((directory / 'rollback-r8-payload.tar.gz').read_bytes(), backward)
    return {'passed': True, 'phase': 'read-only-offline-cohort-audit', 'cohort_id': cohort['cohort_id'],
            'new_manifest_sha256': cohort['new_manifest_sha256'], 'result_sha256': file_sha(directory / 'result.json'),
            'device_accessed': False, 'installed': False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check-local', 'build', 'audit'], nargs='?', default='check-local')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    need(args.action == 'build' or not args.execute, '--execute applies only to offline build')
    need(args.action != 'build' or args.execute, 'offline materialization requires explicit --execute')
    pins, cohort, forward, backward = local_inputs()
    if args.action == 'check-local':
        result = {'passed': True, 'phase': 'read-only-offline-input-check', 'cohort_id': pins['cohort_id'],
                  'new_manifest_sha256': cohort['new_manifest_sha256'], 'output_exists': OUT.exists(),
                  'device_accessed': False, 'tools_executed': False}
    elif args.action == 'build':
        result = materialize(OUT, cohort, forward, backward)
    else:
        result = audit(OUT, cohort, forward, backward)
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
