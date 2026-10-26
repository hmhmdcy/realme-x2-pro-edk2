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
    need(proof['schema'] == 'samurai-irq-native-pm-completed-module-input-v1', 'actual completed module schema')
    for key, expected in {
        'delivery': '0ec51a553c0dedd7c7c4eac511af04291f52c8054c65118944c3b1fefbe54a08',
        'receipt': '407df1f2c41227594d6f49455050838c13f8f3abcf5d2fb3ebb948970037e096',
        'identity': '7890c37084f69e7a62ceada487a061e759171c6c40a3cc833a6096ff124ce7e1',
        'execution': '4e8c03fcc5459376d5f6724c4cac6e8eecd9888240db9e3557a919b82ac981c0',
        'source_delivery': 'fa38684a6f618bd6d081b420c1323f8f146ac5af6174e3695e2a8b40bed7975f',
    }.items():
        need(proof[key]['sha256'] == expected, 'actual completed module input: ' + key)
    pins = json.loads((HERE / 'input-pins.json').read_bytes())
    files = {}

    def read(name, row):
        path = pinned(row)
        files[name] = dict(row)
        return path.read_bytes()

    delivery, receipt, execution, identity, source = [json.loads(read('module_' + name, proof[name]))
        for name in ['delivery', 'receipt', 'execution', 'identity', 'source_delivery']]
    need(delivery['files']['ko-result.json']['sha256'] == proof['receipt']['sha256'] and
         delivery['files']['module-identity.json']['sha256'] == proof['identity']['sha256'] and
         delivery['files']['execution-receipt.json']['sha256'] == proof['execution']['sha256'], 'module delivery binds actual receipts')
    image_receipts = {name: json.loads(read(name, row)) for name, row in pins['receipts'].items()}
    image = image_receipts['Image504_build']['build']
    need(image_receipts['Image504_build']['passed'] is True and image['passed'] is True and
         image['identity']['KBUILD_BUILD_VERSION'] == '504' and
         image['outputs']['arch/arm64/boot/Image'] == {'sha256': IMAGE, 'bytes': 59243008}, 'actual completed Image504')
    need(image['config_exact_original'] is True and image['release_unchanged'] is True and
         image['initramfs_unchanged'] is True and image['B_default_false_unchanged'] is True and
         image['source_sha256'] == '0014077792948460fc2a2e9581225dc684cba4d5bff95c3e88767d661ce5439b' and
         image['compatibility']['public_headers_unchanged'] is True and
         image['compatibility']['actual_ELF_export_names_exact_502'] is True and
         image['compatibility']['builtin_export_rows_exact_502'] is True, 'Image504 original502/BQ/ABI gates')
    new_usb = read('new_USB', proof['module'])
    new_identity = module_identity(new_usb, USB)
    validate_module_completion(delivery, receipt, execution, identity, source, new_identity, image)
    need(len(new_usb) == receipt['module_bytes'] and sha(new_usb) == receipt['module_sha256'], 'actual new USB file')
    need(local(receipt['exported_private_module_path']).resolve() == local(proof['module']['path']).resolve(), 'actual exported module path')
    old_raw = read('base_manifest', pins['base_manifest'])
    old = json.loads(old_raw)
    validate_current_tuple(old, pins['carriers'])
    old_usb = read('old_USB', pins['old_USB'])
    old_identity = module_identity(old_usb, USB)
    need(sha(old_usb) == OLD_USB and old_identity['resident_note_sha256'] ==
         'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d', 'actual current7cb USB')
    current = json.loads(read('current_payload_receipt', pins['current_payload_receipt']))
    actual = json.loads(read('current_update_summary', pins['current_update_summary']))
    need(current['passed'] is True and current['new_manifest_sha256'] == BASE and
         current['new_charger']['sha256'] == CHARGER and
         actual['passed'] is True and actual['installed'] is True and actual['same_boot'] is True and
         actual['new_manifest_sha256'] == BASE and actual['new_charger_sha256'] == CHARGER and
         actual['worker_and_supervisor_wait_zero_reviewed'] is True, 'actual current97c/18e8 update lineage')
    kept, kept_identities = {}, {}
    for target, row in pins['retained'].items():
        raw = read('retained:' + target, row)
        kept[target] = sha(raw)
        if target != '/usr/local/sbin/samurai-usb':
            need(kept[target] == old['installed_files'][target], 'retained current file: ' + target)
        if target.endswith('.ko'):
            name = target.rsplit('/', 1)[1][:-3]
            kept_identities[name] = module_identity(raw, name)
    need(kept['/usr/local/sbin/samurai-usb'] == '2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a', 'actual startup500 retained')
    manager = local(pins['retained']['/usr/sbin/samurai-charging']['path']).read_text()
    need('adapter_revision' not in manager, 'original manager accepts independent revision')
    for name, row in pins['carriers'].items():
        pinned(row)
        files['carrier:' + name] = dict(row)
    carrier = pins['carrier']
    carrier_receipt = json.loads(read('carrier_receipt', carrier['receipt']))
    validate_carrier(carrier_receipt, carrier, image['outputs']['arch/arm64/boot/Image'])
    need(carrier['logdump']['sha256'] == FORWARD_FAT and carrier['logdump']['bytes'] == 67108864, 'exact completed4453 FAT')
    pinned(carrier['logdump'])
    files['carrier:forward_logdump'] = dict(carrier['logdump'])
    for name in ['input-pins.json', 'module-input.json', 'source-pins.json']:
        path = HERE / name
        files[name] = {'path': str(path), 'sha256': file_sha(path), 'bytes': path.stat().st_size}
    for name, row in json.loads((HERE / 'source-pins.json').read_bytes()).items():
        pinned(row)
        files['source:' + name] = dict(row)
    new_raw = make_manifest(old_raw, sha(new_usb))
    check_manifest_delta(old_raw, new_raw, sha(new_usb))
    forward = {TARGET: new_usb, MANIFEST: new_raw}
    backward = {TARGET: old_usb, MANIFEST: old_raw}
    cohort = {'schema': 'samurai-irq-native-pm-budget504-offline-cohort-v1',
              'cohort_id': REVISION, 'status': 'offline-materialized-not-installed', 'release': RELEASE,
              'old_manifest_sha256': BASE, 'new_manifest_sha256': sha(new_raw),
              'adapter_revision': REVISION, 'USB_identities': {'old': old_identity, 'new': new_identity},
              'module_strong_import_count': receipt['strong_import_count'],
              'retained_files': kept, 'retained_module_identities': kept_identities,
              'required_Image504': {'sha256': IMAGE, 'bytes': 59243008},
              'required_logdump': {'sha256': FORWARD_FAT, 'bytes': 67108864},
              'unchanged_boot': {'sha256': BOOT, 'bytes': 100663296},
              'native_DTB': {'sha256': DTB, 'bytes': 116124},
              'rollback': {'USB_sha256': OLD_USB, 'manifest_sha256': BASE,
                           'logdump_sha256': ROLLBACK_FAT, 'boot_unchanged': True,
                           'normal_restart_to_align_resident_required': True},
              'policy': {'default_input_cap_ua': 900000, 'default_charge_cap_ua': 250000,
                         'source_budget_enforced': True, 'startup_requested_ma': 500},
              'stage_only_result': 'staged/runtime_pending', 'module_hot_unload': False,
              'installed': False, 'new_independent_transaction_required': True,
              'scope': 'current IRQ DT/provider plus native DEVICE/on-active system-PM software budget fence',
              'runtime_or_type_ABI_attested': False, 'PM_unwind_complete': False,
              'auto_direct_complete_supported': False,
              'acceptance_pending': ['matching new504 boot and disk/resident USB identity',
                                     'actual IRQs and DWC consumer/provider PM link/callback order',
                                     'safe allowance revoke and fresh post-resume allowance',
                                     'NCM/strict-key recovery and unchanged charging/protection policy'],
              'input_files': files}
    return cohort, forward, backward


def validate_module_completion(delivery, receipt, execution, identity, source, parsed, image):
    expected_sha = 'd04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037'
    expected_note = '08523f9f969b00a278a87ddd5d27ec3b54ac9b53a9c84f6429c4ecf5934c0f3f'
    need(delivery['passed'] is True and receipt['passed'] is True and source['passed'] is True,
         'completed new IRQ+PM module/source')
    need(delivery['module_sha256'] == receipt['module_sha256'] == parsed['sha256'] == identity['module_sha256'] == expected_sha and
         delivery['module_bytes'] == receipt['module_bytes'] == parsed['bytes'] == identity['module_bytes'] == 92144 and
         delivery['module_note_sha256'] == receipt['module_note_sha256'] == parsed['resident_note_sha256'] == identity['module_note_sha256'] == expected_note,
         'actual d046/0852 module and ELF note')
    need(delivery['source_delivery_sha256'] == receipt['IRQ_source_delivery_sha256'] == identity['source_delivery_sha256'] ==
         'fa38684a6f618bd6d081b420c1323f8f146ac5af6174e3695e2a8b40bed7975f' and
         source['files']['samurai-usb-input.c']['sha256'] == receipt['source_sha256'] == identity['source_sha256'] ==
         'cf3c7f039035f7bd1e654e3d781e5f6f16ca01b0fc422234ee71aefd87cc6b3f' and
         receipt['decoder_sha256'] == identity['decoder_sha256'] ==
         'a17caa2cbeb2352da249474e0265fa96745f544d96a29d0ebe8f14c656d548fd', 'actual IRQ+PM source binding')
    need(delivery['actual_strong_import_count'] == receipt['strong_import_count'] == identity['strong_import_count'] == 47 and
         receipt['weak_import_count'] == identity['weak_import_count'] == 0 and
         receipt['unresolved_strong_imports'] == [] and receipt['imports_all_from_Image502_builtin'] is True and
         receipt['no_module_provider_fallback'] is True and receipt['diagnostics'] == [], 'actual47 builtin imports')
    need(receipt['release'] == RELEASE and receipt['intree'] == 'Y' and parsed['intree'] == 'Y' and
         receipt['actual_config_values_exact_Image502'] is True and receipt['generated_autoconf_exact_Image502'] is True and
         receipt['Image502_exports_sha256'] == image['outputs']['vmlinux.symvers']['sha256'], 'actual504 export/config lineage')
    need(execution['outer_exec_terminal'] is True and execution['outer_exec_exit_code'] == 0 and
         execution['commands'] == receipt['commands'] and len(receipt['commands']) == 2 and
         all(c['terminal'] is True and c['returncode'] == 0 for c in receipt['commands']) and
         [c['argv'][-1] for c in receipt['commands']] == ['modules_prepare', 'drivers/power/supply/samurai-usb-input.ko'] and
         receipt['tracked_shared_R7_Image502_inputs_unchanged'] is True and receipt['before'] == receipt['after'],
         'actual original two-child completion and parent inputs')


def materialize(cohort, forward, backward):
    out = local(OUT)
    out.mkdir(mode=0o700, exist_ok=False)
    report = {'passed': False, 'installed': False, 'device_accessed': False,
              'source_sha256': file_sha(Path(__file__)),
              'input_pins_sha256': file_sha(HERE / 'input-pins.json'),
              'module_input_sha256': file_sha(HERE / 'module-input.json')}
    try:
        blobs = {'manifest.json': forward[MANIFEST], 'rollback-manifest.json': backward[MANIFEST],
                 'cohort.json': encode(cohort), 'irq-native-pm-payload.tar.gz': archive(forward),
                 'rollback-7cb-18e8-payload.tar.gz': archive(backward)}
        for name, raw in blobs.items():
            with (out / name).open('xb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        check_archive((out / 'irq-native-pm-payload.tar.gz').read_bytes(), forward)
        check_archive((out / 'rollback-7cb-18e8-payload.tar.gz').read_bytes(), backward)
        need((out / 'manifest.json').read_bytes() == forward[MANIFEST] and
             (out / 'rollback-manifest.json').read_bytes() == backward[MANIFEST], 'exact manifest readback')
        for row in cohort['input_files'].values():
            pinned(row)
        report.update(passed=True, files={name: {'sha256': file_sha(out / name), 'bytes': len(raw)}
                                          for name, raw in blobs.items()},
                      original_inputs_unchanged=True, rootfs_member_count=2)
    except BaseException as error:
        report.update(error=repr(error), replay_permitted=False)
        raise
    finally:
        with (out / 'result.json').open('xb') as stream:
            stream.write(encode(report))
            stream.flush()
            os.fsync(stream.fileno())
    return report


def audit(cohort, forward, backward):
    out = local(OUT)
    result = json.loads((out / 'result.json').read_bytes())
    need(result['passed'] is True and result['source_sha256'] == file_sha(Path(__file__)) and
         result['input_pins_sha256'] == file_sha(HERE / 'input-pins.json') and
         result['module_input_sha256'] == file_sha(HERE / 'module-input.json'), 'original materialization binding')
    need(set(result['files']) == {'manifest.json', 'rollback-manifest.json', 'cohort.json',
                                  'irq-native-pm-payload.tar.gz', 'rollback-7cb-18e8-payload.tar.gz'},
         'exact saved output set')
    for name, row in result['files'].items():
        need(file_sha(out / name) == row['sha256'] and (out / name).stat().st_size == row['bytes'], 'saved bytes: ' + name)
    need((out / 'cohort.json').read_bytes() == encode(cohort) and
         (out / 'manifest.json').read_bytes() == forward[MANIFEST] and
         (out / 'rollback-manifest.json').read_bytes() == backward[MANIFEST], 'saved current identities')
    check_archive((out / 'irq-native-pm-payload.tar.gz').read_bytes(), forward)
    check_archive((out / 'rollback-7cb-18e8-payload.tar.gz').read_bytes(), backward)
    return {'passed': True, 'phase': 'read-only-offline-audit', 'installed': False, 'device_accessed': False}


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
        cohort, forward, backward = local_inputs()
        if args.action == 'build':
            result = materialize(cohort, forward, backward)
        elif args.action == 'audit':
            result = audit(cohort, forward, backward)
        else:
            result = {'passed': True, 'phase': 'read-only-input-check',
                      'new_manifest_sha256': cohort['new_manifest_sha256'],
                      'output_exists': local(OUT).exists(), 'installed': False, 'device_accessed': False}
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
