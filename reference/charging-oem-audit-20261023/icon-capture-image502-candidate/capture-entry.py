"""Thin read-only identity/sample adapter for the byte-frozen icon worker."""
from pathlib import Path
import hashlib
import json
import os
import worker as collector

REQUEST = Path(__file__).with_name('request-private.json')
GUARD = '/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt'


class CaptureCycle(collector.Cycle):
    """Keep the original off/gap rules; observe 90 seconds after stable on."""
    def feed(self, row):
        phase = super().feed(row)
        if phase == 'complete' and row['t_end'] - self.settle_at < 90:
            self.complete = False
            return 'settling'
        return phase


class CaptureIO(collector.RealIO):
    def check_identity(self, config):
        super().check_identity(config)
        request = json.loads(REQUEST.read_bytes())
        expected = request['identity_expected']
        if not (request['transaction'] == config['transaction']
                and request['expected_boot'] == config['boot_id']
                and request['manifest_sha256'] == config['manifest_sha256']
                and request['guard_path'] == GUARD
                and Path(GUARD).read_text().strip() == config['boot_id']
                and os.uname().release == expected['release']
                and os.uname().version == expected['version']
                and hashlib.sha256(Path('/etc/samurai-rootfs-release').read_bytes()).hexdigest() == expected['rootfs']):
            raise ValueError('adopted EUD-off guard/kernel/rootfs changed')
        for name, digest in expected['notes'].items():
            parent = Path('/sys/module') / name
            if (hashlib.sha256((parent / 'notes/.note.gnu.build-id').read_bytes()).hexdigest() != digest
                    or (parent / 'initstate').read_text().strip() != 'live'):
                raise ValueError('adopted R8/camera481 live note changed: ' + name)

    def sample(self, base):
        row = super().sample(base)
        ps = Path('/sys/class/power_supply')
        row['extended_read_t_start'] = row['t_end']
        row['source'] = {key: self.read(ps / 'samurai-usb-input' / filename, numeric)
                         for key, filename, numeric in [
                             ('usb_type', 'usb_type', False), ('current_max_ua', 'current_max', True),
                             ('input_current_limit_ua', 'input_current_limit', True)]}
        row['hardware_input'] = {'input_current_limit_ua': self.read(ps / 'mp2650-input/input_current_limit', True),
                                 'status': self.read(ps / 'mp2650-input/status')}
        row['udc'] = {key: self.read(Path('/sys/class/udc/a600000.usb') / key)
                      for key in ['state', 'current_speed']}
        row['MaxPower_ma'] = self.read('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower', True)
        row['battery']['current_avg_ua'] = self.read(self.battery / 'current_avg', True)
        row['t_end'] = collector.time.monotonic() - base
        return row


def main(argv=None):
    original = collector.RealIO
    original_cycle = collector.Cycle
    collector.RealIO = CaptureIO
    collector.Cycle = CaptureCycle
    try:
        return collector.main(argv)
    finally:
        collector.RealIO = original
        collector.Cycle = original_cycle


if __name__ == '__main__':
    raise SystemExit(main())
