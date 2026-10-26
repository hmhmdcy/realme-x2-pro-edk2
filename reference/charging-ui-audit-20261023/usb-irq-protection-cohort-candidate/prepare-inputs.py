"""Freeze real cached inputs only after both module deliveries exist; no device IO."""
from pathlib import Path
import argparse
import hashlib
import json

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
PRIVATE = Path('E:/edk2-samurai-out/charging-management-20261023')

def need(value, message):
    if not value:
        raise ValueError(message)

def row(path, expected=None):
    path = Path(path).resolve()
    need(path.is_file() and not path.is_symlink(), 'missing input: ' + str(path))
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    need(expected is None or digest == expected, 'frozen input changed: ' + str(path))
    return {'path': str(path), 'sha256': digest, 'bytes': path.stat().st_size}

def prepare():
    board = REF / 'charging-ui-audit-20261023/usb-input-irq-board-candidate'
    boot = REF / 'charging-ui-audit-20261023/usb-input-irq-boot-candidate'
    protection = REF / 'charging-oem-audit-20261023/protection-query-observer-module-candidate'
    observer = REF / 'charging-oem-audit-20261023/protection-query-observer-candidate'
    logdump = REF / 'charging-session-20261023/gauge-image502-logdump-candidate'
    retained = REF / 'charging-session-20261023/r8-source-integration/rootfs-sources'
    p_delivery = row(protection / 'delivery.json', 'de4b680cbc809b48ff6a8b48f6c3a0b0e3164b21a2d7ca78b24be95735835b40')
    for name, entry in json.loads(Path(p_delivery['path']).read_bytes())['files'].items():
        row(protection / name, entry['sha256'])
    receipts = {
        'protection_delivery': p_delivery,
        'protection_ko': row(protection / 'ko-result.json', '9626534ca5d7c91d2e4aad87ef462f76bf193899fd903c36be80950cbd796437'),
        'protection_identity': row(protection / 'module-identity.json', '3caa749b8e393509198740acfbbc8acf8586ac2dab6d47a7899a48c110798581'),
        'observer_source_delivery': row(observer / 'delivery.json', '907fc1245576eee21b3d5231c25359f6d101e1f537ea8ff423ee21139392a304'),
        'observer_independent_review': row(REF / 'charging-ui-audit-20261023/protection-query-observer-independent-review/review-result.json', 'faaf494ae0abfbf96725822240c71b8abcd7863116732409a119206e49e20830'),
        'USB_ko': row(board / 'ko-result.json', 'c710bd53c9ed8188fa144d64985d948c3c66e73eae63c9c062260e88bfeadd31'),
        'DT_pair': row(board / 'pair-manifest.json', '1d1e65c1e29a25694906f1c3004972e751209b5562e070bec885ced35bcafb16'),
        'DT_result': row(board / 'dt-result.json', 'a055ee096cc1bcb0f6082570be93518a1fd6cdf610315d93b7fa1d5e7e29b0e8'),
        'boot': row(boot / 'delivery.json', 'ea2ff2952a13eddd205ec9ec79e075a42c1a6060c8234f8f6765d03860d7faeb'),
        'boot_result': row(boot / 'result.json', '2dc2d78151655970155d649589e1a1ec1a4dc215709e0e4a4b5cdca133ee34fd'),
        'logdump': row(logdump / 'delivery.json'),
        'logdump_result': row(logdump / 'logdump-result.json', 'c08d98309b9c789f1f499d08b03ab53c1648c2d5e1efb39359dd7371570e6758'),
    }
    return {
        'schema': 'samurai-usb-irq-protection-cohort-inputs-v1',
        'cohort_id': 'usb-irq-protection-observer-01',
        'adapter_revision': 'usb-irq-protection-observer-01',
        'base_manifest': row(PRIVATE / 'r8-candidate/manifest.json', '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'),
        'modules': {
            'samurai-usb-input': row(PRIVATE / 'usb-input-irq-board-private-01/samurai-usb-input-irq-private.ko', '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f'),
            'samurai-gauge-protection': row(PRIVATE / 'protection-query-observer-module-private-01/samurai-gauge-protection-observer-private.ko', '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044'),
        },
        'old_USB': row(PRIVATE / 'r7-candidate/samurai-usb-input.ko', '7d4e0f948b993a6e0cc9459bac4ade2db2fe7b88ce7b7d462ea34bcb933c4f70'),
        'old_protection_archive': row(PRIVATE / 'r5-deployed-snapshot/samurai-charging-payload.tar.gz', '829178e5fdccb3f94766eb667594a3a89103580ef9a695905c90a24da17669dc'),
        'retained': {
            '/usr/sbin/samurai-charging': row(retained / 'usr/sbin/samurai-charging', '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4'),
            '/etc/init.d/samurai-charging': row(retained / 'etc/init.d/samurai-charging', 'bfed48ebbcaced5f017110564045eef500a88f12fefe7ebff6d1e74cabfe570a'),
            '/usr/lib/samurai-charging/control-trial.py': row(retained / 'usr/lib/samurai-charging/control-trial.py', 'c33cb2eec24031e72a5f1dda9b94c05607615e0b12a14ba3cecd6db56c820761'),
            '/usr/lib/samurai-charging/live-session.py': row(retained / 'usr/lib/samurai-charging/live-session.py', '2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b'),
            '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko': row(PRIVATE / 'r8-candidate/samurai-mp2650.ko', '10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f'),
            '/usr/local/sbin/samurai-usb': row(PRIVATE / 'usb500-default-r1-private/samurai-usb-500-r2-private.sh', '2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a'),
        },
        'carriers': {
            'boot': row(PRIVATE / 'usb-input-irq-boot-private-01/boot-usb-input-irq-private.img', 'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'),
            'native_DTB': row(PRIVATE / 'usb-input-irq-board-private-01/samurai-usb-input-irq-native-private.dtb', '13d359c4a78ed423d52f1d5e09345c7dc7032811fabe786952ac11e868adee9f'),
            'logdump': row(PRIVATE / 'gauge-image502-logdump-private-01/logdump-gauge502-private.img', 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'),
            'Image502_sha256': '085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955',
            'rollback_boot': row(PRIVATE / 'gauge-image501-boot-private-01/boot-gauge501-private.img', '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'),
        },
        'receipts': receipts,
    }

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    data = prepare()
    if args.execute:
        with (HERE / 'input-pins.json').open('xb') as stream:
            stream.write((json.dumps(data, indent=2) + '\n').encode())
    print(json.dumps({'passed': True, 'input_pins_written': args.execute, 'device_accessed': False}))
