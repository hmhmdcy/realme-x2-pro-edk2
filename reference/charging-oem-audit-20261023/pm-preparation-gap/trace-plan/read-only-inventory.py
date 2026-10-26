"""Read-only Linux-root inventory. No trace setup, waits, PM or device writes.

Pass a saved filesystem mirror, or explicitly / on a future authorized target.
This file has only been tested against an offline fixture, never the phone.
"""
from pathlib import Path
import argparse
import collections
import json
import os
import struct
import time
import zlib

EVENTS = (
    'power/suspend_resume', 'power/device_pm_callback_start',
    'power/device_pm_callback_end', 'power/wakeup_source_activate',
    'power/wakeup_source_deactivate', 'sched/sched_switch',
    'sched/sched_wakeup', 'lock/contention_begin', 'lock/contention_end',
    'printk/console', 'irq/irq_handler_entry', 'irq/irq_handler_exit',
    'rtc/rtc_set_alarm', 'rtc/rtc_alarm_irq_enable', 'rtc/rtc_timer_fired',
)


def journal_summary(data):
    if len(data) < 48:
        raise ValueError('short header')
    magic, version, size, count, width, first, last, crc, reserved = \
        struct.unpack_from('<8sIIIIQQII', data)
    if (magic != b'EUDTXJ48' or version != 1 or width != 6 or
            count > 512 or size != 48 + count * width or len(data) != size or
            reserved or (count and first != last - count + 1) or
            (not count and first)):
        raise ValueError('invalid journal header')
    copy = bytearray(data)
    copy[40:44] = bytes(4)
    if zlib.crc32(copy) != crc:
        raise ValueError('journal CRC mismatch')
    stats = collections.defaultdict(lambda: {'frames': 0, 'bytes': 0})
    for offset in range(48, len(data), width):
        length, source = struct.unpack_from('<BB', data, offset)
        if not 1 <= length <= 4 or source not in (1, 2):
            raise ValueError('invalid journal record')
        key = 'tty' if source == 1 else 'console'
        stats[key]['frames'] += 1
        stats[key]['bytes'] += length
    return {'first_frame_seq': first, 'last_frame_seq': last,
            'retained_frames': count, 'tail_by_source': dict(stats),
            'records_are_issued_mmio_not_ack': True}


def inventory(root, pid=None):
    root = Path(root)
    def read(name, limit=65536, binary=False):
        try:
            with (root / name.lstrip('/')).open('rb') as f:
                value = f.read(limit + 1)
            if len(value) > limit:
                return {'error': 'over_size_limit', 'limit': limit}
            return value if binary else value.decode(errors='replace').strip()
        except OSError as e:
            return {'error': type(e).__name__, 'errno': e.errno}

    result = {'readonly': True, 'pm_entered': False,
              'monotonic_ns': time.monotonic_ns()}
    for name in ('proc/sys/kernel/osrelease', 'proc/consoles',
                 'proc/sys/kernel/printk',
                 'sys/module/printk/parameters/console_suspend',
                 'sys/module/printk/parameters/ignore_loglevel',
                 'sys/class/tty/console/active'):
        result[name] = read(name)
    cmdline = read('proc/cmdline')
    result['cmdline_console_tokens_only'] = (
        [word for word in cmdline.split() if word.startswith(
            ('console=', 'earlycon=', 'loglevel=', 'log_buf_len=',
             'printk.ignore_loglevel=', 'printk.console_suspend=')) or word in
            ('no_console_suspend', 'keep_bootcon', 'ignore_loglevel')]
        if isinstance(cmdline, str) else cmdline)
    device = 'sys/bus/platform/devices/88e0000.serial'
    try:
        result['eud_driver_link'] = os.readlink(root / device / 'driver')
    except OSError as e:
        result['eud_driver_link'] = {'error': type(e).__name__, 'errno': e.errno}
    result['eud_compatible'] = read(device + '/of_node/compatible', 512)
    for name in ('rx_stats', 'irq_watch', 'console_rx'):
        result['eud_' + name] = read(device + '/' + name, 4096)
    raw = read(device + '/tx_journal', 3120, True)
    try:
        result['eud_tx_journal'] = journal_summary(raw) if isinstance(raw, bytes) else raw
    except ValueError as e:
        result['eud_tx_journal'] = {'error': str(e)}
    trace = next((p for p in ('sys/kernel/tracing', 'sys/kernel/debug/tracing')
                  if (root / p / 'available_events').is_file()), None)
    result['tracefs'] = trace
    if trace:
        for name in ('current_tracer', 'available_tracers', 'trace_clock'):
            result[name] = read(trace + '/' + name)
        available = read(trace + '/available_events', 131072)
        result['selected_available_events'] = (
            sorted(set(available.splitlines()) &
                   {event.replace('/', ':') for event in EVENTS})
            if isinstance(available, str) else available)
        result['selected_formats'] = {
            event: read(trace + '/events/' + event + '/format', 8192)
            for event in EVENTS}
        result['sched_stacktrace_trigger_catalog'] = read(
            trace + '/events/sched/sched_switch/trigger', 8192)
    if pid:
        result['selected_process'] = {
            name: read('proc/' + str(pid) + '/' + name, 16384)
            for name in ('comm', 'wchan', 'stack', 'stat', 'schedstat')}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', help='Explicit filesystem root or saved mirror')
    parser.add_argument('--pid', type=int, help='One already identified PM/printer PID')
    args = parser.parse_args()
    if args.pid is not None and args.pid <= 0:
        parser.error('PID must be positive')
    print(json.dumps(inventory(args.root, args.pid), indent=2))
