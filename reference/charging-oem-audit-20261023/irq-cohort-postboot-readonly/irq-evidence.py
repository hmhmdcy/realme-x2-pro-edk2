"""Read-only named IRQ/OF evidence. Counts alone do not establish causality."""
from pathlib import Path
import base64
import re
import struct
import time

NAMES = ('usbin-plugin', 'usbin-src-change')
NODE = '/sys/firmware/devicetree/base/soc@0/spmi@c440000/pmic@2/usb-input@1300'
PROPERTIES = {'compatible': b'realme,rmx1931-usb-input\0', 'reg': struct.pack('>I', 0x1300),
              'interrupts': struct.pack('>8I', 2, 0x13, 4, 3, 2, 0x13, 6, 1),
              'interrupt-names': b'usbin-plugin\0usbin-src-change\0', 'status': b'okay\0'}


def parse_interrupts(text):
    if not isinstance(text, str):
        raise ValueError('unreadable /proc/interrupts')
    lines = text.splitlines()
    if not lines:
        raise ValueError('missing CPU header')
    cpus = lines[0].split()
    if not cpus or len(cpus) > 256 or len(set(cpus)) != len(cpus) or not all(re.fullmatch(r'CPU[0-9]+', c) for c in cpus):
        raise ValueError('invalid CPU header')
    found = {}
    for line in lines[1:]:
        match = re.match(r'^\s*([0-9]+):\s+(.*)$', line)
        if not match:
            continue
        columns = match[2].split()
        mentioned = [name for name in NAMES if name in re.split(r'[\s,]+', match[2])]
        if not mentioned:
            continue
        if len(mentioned) != 1:
            raise ValueError('ambiguous/shared named IRQ')
        name = mentioned[0]
        if name in found or len(columns) <= len(cpus) or ',' in match[2] or columns[-1] != name:
            raise ValueError('ambiguous/shared named IRQ')
        counts = columns[:len(cpus)]
        if not all(re.fullmatch(r'[0-9]+', count) for count in counts):
            raise ValueError('invalid per-CPU IRQ count')
        if not 0 < int(match[1]) < (1 << 31) or any(int(count) >= (1 << 64) for count in counts):
            raise ValueError('out-of-range IRQ or counter')
        found[name] = {'irq': int(match[1]), 'counts': dict(zip(cpus, map(int, counts))),
                       'controller_and_action': ' '.join(columns[len(cpus):]), 'raw_line': line}
    if set(found) != set(NAMES) or len({r['irq'] for r in found.values()}) != 2:
        raise ValueError('both unique named IRQ registrations required; polling is insufficient')
    return {'cpus': cpus, 'named': found}


def snapshot():
    started = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    device = Path('/sys/class/power_supply/samurai-usb-input/device').resolve(strict=True)
    providers = []
    for path in Path('/sys/bus/platform/devices').iterdir():
        driver = path / 'driver'
        if driver.is_symlink() and driver.resolve(strict=True).name == 'samurai-usb-input':
            providers.append(str(path.resolve(strict=True)))
    result = {'started_boottime_ns': started,
            'device': str(device), 'driver': (device / 'driver').resolve(strict=True).name,
            'of_node': str((device / 'of_node').resolve(strict=True)), 'bound_providers': sorted(providers),
            'properties_b64': {name: base64.b64encode((Path(NODE) / name).read_bytes()).decode()
                               for name in PROPERTIES},
            'proc_interrupts': Path('/proc/interrupts').read_text()}
    result['ended_boottime_ns'] = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    return result


def validate_snapshot(raw):
    if not (isinstance(raw, dict) and raw.get('driver') == 'samurai-usb-input' and raw.get('of_node') == NODE):
        raise ValueError('supply must use the real native OF provider')
    if not isinstance(raw.get('device'), str) or not raw['device'].startswith('/sys/devices/') or raw.get('bound_providers') != [raw['device']]:
        raise ValueError('duplicate/missing bound USB provider')
    if not (0 <= raw['started_boottime_ns'] <= raw['ended_boottime_ns']):
        raise ValueError('invalid IRQ evidence interval')
    if set(raw['properties_b64']) != set(PROPERTIES):
        raise ValueError('missing native IRQ properties')
    for name, expected in PROPERTIES.items():
        if base64.b64decode(raw['properties_b64'][name], validate=True) != expected:
            raise ValueError('wrong OEM IRQ property: ' + name)
    return parse_interrupts(raw['proc_interrupts'])


def delta(before, after):
    a, b = validate_snapshot(before), validate_snapshot(after)
    result = {'comparable': False, 'positive_counts': {}, 'physical_delivery_accepted': False}
    if before['device'] != after['device'] or before['of_node'] != after['of_node']:
        return dict(result, reason='provider changed')
    if after['started_boottime_ns'] < before['ended_boottime_ns']:
        return dict(result, reason='intervals overlap or reverse')
    if a['cpus'] != b['cpus']:
        return dict(result, reason='online CPU set changed; totals cannot be compared')
    increments = {}
    for name in NAMES:
        old, new = a['named'][name], b['named'][name]
        if old['irq'] != new['irq']:
            return dict(result, reason='Linux IRQ mapping changed')
        values = {cpu: new['counts'][cpu] - old['counts'][cpu] for cpu in a['cpus']}
        if any(value < 0 for value in values.values()):
            return dict(result, reason='per-CPU counter regressed')
        increments[name] = {'irq': new['irq'], 'per_cpu': values, 'sum': sum(values.values())}
    return dict(result, comparable=True, reason=None, increments=increments,
                positive_counts={name: item['sum'] > 0 for name, item in increments.items()})


def check_postboot(raw):
    first, last = raw['irq_before'], raw['irq_after']
    a, b = validate_snapshot(first), validate_snapshot(last)
    if first['device'] != last['device'] or any(a['named'][n]['irq'] != b['named'][n]['irq'] for n in NAMES):
        raise ValueError('provider/IRQ instance changed during postboot collection')
    if not (raw['started_boottime_ns'] <= first['started_boottime_ns'] <= first['ended_boottime_ns']
            <= last['started_boottime_ns'] <= last['ended_boottime_ns'] <= raw['ended_boottime_ns']):
        raise ValueError('IRQ snapshots outside collection interval')
    return {'native_OF_provider_and_exact_IRQ_properties': True, 'both_named_IRQs_registered': True,
            'Linux_IRQs': {name: b['named'][name]['irq'] for name in NAMES},
            'interval_delta': delta(first, last), 'IRQ_delivery_or_icon_latency_accepted': False}
