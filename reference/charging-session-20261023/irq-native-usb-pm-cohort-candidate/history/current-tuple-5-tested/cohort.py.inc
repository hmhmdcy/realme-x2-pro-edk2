"""Offline current-IRQ USB PM pair; no device access, staging or installer."""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RELEASE = '7.3.0-rc6-rmx1931-samurai-k363+'
USB = 'samurai-usb-input'
TARGET = '/lib/modules/' + RELEASE + '/extra/samurai-charging/' + USB + '.ko'
MANIFEST = '/usr/share/samurai-charging/manifest.json'
BASE = '18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'
OLD_USB = '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f'
CHARGER = '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd'
PROTECTION = '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044'
OLD_REVISION = 'usb-irq-protection-observer-01'
REVISION = 'usb-irq-native-pm-budget504-01'
BOOT = 'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
DTB = '13d359c4a78ed423d52f1d5e09345c7dc7032811fabe786952ac11e868adee9f'
IMAGE = 'f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4'
FORWARD_FAT = '4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83'
ROLLBACK_FAT = 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
OUT = Path('E:/edk2-samurai-out/charging-management-20261023/irq-native-usb-pm-budget504-cohort-private-01')
METHOD = HERE.parent / 'native-usb-pm-cohort-candidate/cohort.py'
METHOD_SHA = '911d1ebd06fcf852ff0f8bddcb1c8d2caf69dbe38eeeebbf71c83b506abbd8e3'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def local(path):
    text = str(path).replace('\\', '/')
    if os.name == 'nt' and text.startswith('/mnt/e/'):
        text = 'E:/' + text[7:]
    elif os.name != 'nt' and text.startswith('E:/'):
        text = '/mnt/e/' + text[3:]
    return Path(text)


need(sha(METHOD.read_bytes()) == METHOD_SHA, 'frozen pure packaging method')
_spec = importlib.util.spec_from_file_location('_frozen_native_pm_packaging', METHOD)
_method = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_method)
archive = _method.archive
check_archive = _method.check_archive
validate_carrier = _method.validate_carrier
module_identity = _method.module_identity


def encode(value):
    return (json.dumps(value, indent=2) + '\n').encode()


def file_sha(path):
    digest = hashlib.sha256()
    with local(path).open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def pinned(row):
    path = local(row['path'])
    need(path.is_file() and not path.is_symlink(), 'ordinary input file: ' + str(path))
    need(path.stat().st_size == row['bytes'] and file_sha(path) == row['sha256'], 'input bytes: ' + str(path))
    return path


def make_manifest(raw, digest):
    """Preserve every byte except two USB digests and the revision value."""
    need(sha(raw) == BASE, 'exact current18e8 manifest bytes')
    need(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest) and digest != OLD_USB,
         'actual distinct new USB digest')
    old = json.loads(raw)
    need(old['release'] == RELEASE and old['adapter_revision'] == OLD_REVISION, 'current IRQ revision/release')
    need(set(old['modules']) == {USB, 'samurai-mp2650', 'samurai-gauge-protection'}, 'current module set')
    need(old['modules'][USB] == {'target': TARGET, 'sha256': OLD_USB} and
         old['installed_files'][TARGET] == OLD_USB, 'current IRQ USB pair')
    need(old['default_input_cap_ua'] == 900000 and old['default_charge_cap_ua'] == 250000 and
         old['source_budget_enforced'] is True, 'unchanged caps')
    for name, digest_kept in [('samurai-mp2650', CHARGER), ('samurai-gauge-protection', PROTECTION)]:
        entry = old['modules'][name]
        need(entry['sha256'] == digest_kept == old['installed_files'][entry['target']], 'current retained module: ' + name)
    old_revision = json.dumps(OLD_REVISION).encode()
    new_revision = json.dumps(REVISION).encode()
    need(raw.count(OLD_USB.encode()) == 2 and raw.count(old_revision) == 1 and
         digest.encode() not in raw and new_revision not in raw, 'three unambiguous byte replacements')
    result = raw.replace(OLD_USB.encode(), digest.encode()).replace(old_revision, new_revision)
    expected = copy.deepcopy(old)
    expected['modules'][USB]['sha256'] = digest
    expected['installed_files'][TARGET] = digest
    expected['adapter_revision'] = REVISION
    need(json.loads(result) == expected and
         result.replace(digest.encode(), OLD_USB.encode()).replace(new_revision, old_revision) == raw,
         'only two USB hash spans and revision bytes change')
    return result


def check_manifest_delta(old_raw, new_raw, digest):
    need(new_raw == make_manifest(old_raw, digest), 'manifest outside current IRQ USB/revision delta')


def validate_current_tuple(meta, carriers):
    need(meta['modules']['samurai-mp2650']['sha256'] == CHARGER and
         meta['modules']['samurai-gauge-protection']['sha256'] == PROTECTION and
         meta['modules'][USB]['sha256'] == OLD_USB, 'current97c/7848/7cb tuple')
    need({k: (v['sha256'], v['bytes']) for k, v in carriers.items()} == {
        'boot': (BOOT, 100663296), 'native_DTB': (DTB, 116124),
        'rollback_logdump': (ROLLBACK_FAT, 67108864)}, 'current bootedd/IRQ-DT13d3/logdumpace2')


def source_check():
    pins = json.loads((HERE / 'source-pins.json').read_bytes())
    for row in pins.values():
        pinned(row)
    return {'passed': True, 'phase': 'source-only', 'material_inputs_present': (HERE / 'module-input.json').is_file(),
            'output_exists': local(OUT).exists(), 'device_accessed': False, 'payload_created': False}


def local_inputs():
    # Added only after the actual new module has completed; no placeholder identity.
    proof_path = HERE / 'module-input.json'
    need(proof_path.is_file(), 'actual IRQ+PM module input not yet supplied; no package permitted')
    return complete_inputs(json.loads(proof_path.read_bytes()))


def complete_inputs(proof):
    raise ValueError('actual IRQ+PM receipt schema not yet handed over; no package permitted')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', choices=['check-sources', 'check-local', 'build', 'audit'], default='check-sources')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    need(args.execute == (args.action == 'build'), 'only offline build requires --execute')
    source_check()
    if args.action == 'check-sources':
        result = source_check()
    else:
        # No mkdir, archive, device or process operation precedes completed inputs.
        result = local_inputs()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
