"""Fixed PM event evidence. Import/inspection performs no trace writes."""
from pathlib import Path
import errno
import os
import re
import time

REQUIRED = {
    'power/suspend_resume': {'action', 'val', 'start'},
    'power/device_pm_callback_start': {'device', 'driver', 'pm_ops', 'event'},
    'power/device_pm_callback_end': {'device', 'driver', 'error'},
    'irq/irq_handler_entry': {'irq', 'name'},
    'irq/irq_handler_exit': {'irq', 'ret'},
    'rtc/rtc_set_alarm': {'secs', 'err', 'common_pid'},
    'rtc/rtc_alarm_irq_enable': {'enabled', 'err', 'common_pid'},
    'sched/sched_switch': {'prev_pid', 'next_pid', 'prev_state'},
    'lock/contention_begin': {'lock_addr', 'flags', 'common_pid'},
    'lock/contention_end': {'lock_addr', 'ret', 'common_pid'},
}


def fields(text):
    return set(re.findall(r'field:[^;]*?\b([A-Za-z_]\w*)(?:\[[^;]*\])?\s*;', text))


def rtc_irq(text):
    rows = [line for line in text.splitlines() if line.rstrip().endswith('pm8xxx_rtc_alarm')]
    if len(rows) != 1:
        raise ValueError('RTC IRQ missing or ambiguous; never broaden IRQ tracing')
    number, rest = rows[0].split(':', 1)
    if not number.strip().isdigit():
        raise ValueError('invalid RTC IRQ number')
    counts = []
    for item in rest.split():
        if not item.isascii() or not item.isdigit():
            break
        counts.append(int(item))
    if not counts:
        raise ValueError('RTC IRQ CPU counters missing')
    return {'irq': int(number), 'name': 'pm8xxx_rtc_alarm', 'count': sum(counts)}


def optional_wakeup_irq(read):
    try:
        text = read('/sys/power/pm_wakeup_irq').strip()
        if not text.isascii() or not text.isdigit():
            raise ValueError('invalid pm_wakeup_irq')
        return {'available': True, 'value': int(text), 'errno': None}
    except OSError as error:
        return {'available': False, 'value': None, 'errno': error.errno}


class TraceIO:
    def read(self, path):
        return Path(path).read_text()

    def write(self, path, text):
        fd = os.open(path, os.O_WRONLY | os.O_CLOEXEC)
        try:
            body = text.encode()
            if os.write(fd, body) != len(body):
                raise OSError(errno.EIO, 'short tracefs write')
        finally:
            os.close(fd)

    def mkdir(self, path):
        Path(path).mkdir()

    def rmdir(self, path):
        Path(path).rmdir()


def inspect(io, pid, console_pids=(), root='/sys/kernel/tracing'):
    if type(pid) is not int or pid <= 0 or any(type(x) is not int or x <= 0 for x in console_pids):
        raise ValueError('invalid real worker/console PIDs')
    result = {'passed': False, 'formats': {}, 'errors': [], 'root': root,
              'worker_pid': pid, 'console_pids': sorted(set(console_pids)),
              'wakeup_irq': optional_wakeup_irq(io.read)}
    try:
        result['rtc'] = rtc_irq(io.read('/proc/interrupts'))
    except (ValueError, OSError) as error:
        result['errors'].append(str(error))
    try:
        available = set(io.read(root + '/available_events').split())
    except OSError as error:
        available = set()
        result['errors'].append('available_events errno=' + str(error.errno))
    for name, needed in REQUIRED.items():
        try:
            if name.replace('/', ':') not in available:
                raise ValueError('event unavailable')
            text = io.read(root + '/events/' + name + '/format')
            result['formats'][name] = text
            if not needed <= fields(text):
                raise ValueError('required runtime format fields missing')
        except (OSError, ValueError) as error:
            result['errors'].append(name + ': ' + str(error))
    try:
        result['trigger_catalog'] = io.read(root + '/events/sched/sched_switch/trigger')
    except OSError as error:
        result['trigger_catalog'] = ''
        result['errors'].append('trigger catalog errno=' + str(error.errno))
    if 'stacktrace' not in result['trigger_catalog']:
        result['errors'].append('bounded stacktrace trigger unavailable')
    try:
        clocks = io.read(root + '/trace_clock').replace('[', '').replace(']', '').split()
    except OSError as error:
        clocks = []
        result['errors'].append('trace_clock errno=' + str(error.errno))
    result['clock'] = next((name for name in ['boot', 'global', 'mono'] if name in clocks), None)
    if result['clock'] is None:
        result['errors'].append('no supported cross-CPU trace clock')
    result['trace_clock_includes_sleep'] = True if result['clock'] == 'boot' else None
    result['wakeup_source_name_mapping'] = 'unproved; no broad wakeup-source events enabled'
    result['passed'] = not result['errors']
    return result


def normalized(expression):
    return re.sub(r'\s+', '', expression)


class Session:
    """One owned trace instance; all filter readbacks precede any enable."""
    def __init__(self, io, capability, transaction, save_trace):
        if not re.fullmatch(r'charging-pm-current-[a-z0-9][a-z0-9-]{0,32}', transaction):
            raise ValueError('new fixed-scope transaction required')
        self.io, self.cap, self.save_trace = io, capability, save_trace
        self.path = capability['root'] + '/instances/' + transaction
        self.owned = False
        self.filters, self.enabled = [], []
        self.trigger_attempted = False
        self.trace_saved = False

    def setup(self):
        if not self.cap['passed']:
            raise ValueError('required trace capability incomplete before alarm arm')
        self.io.mkdir(self.path)  # existing instance is never owned or removed
        self.owned = True
        self.io.write(self.path + '/tracing_on', '0')
        self.io.write(self.path + '/current_tracer', 'nop')
        self.io.write(self.path + '/buffer_size_kb', '512')
        self.io.write(self.path + '/trace_clock', self.cap['clock'])
        if '[' + self.cap['clock'] + ']' not in self.io.read(self.path + '/trace_clock'):
            raise ValueError('trace clock readback differs')
        pids = sorted({self.cap['worker_pid'], *self.cap['console_pids']})
        chosen = ' || '.join('common_pid == ' + str(pid) for pid in pids)
        prev = ' || '.join('prev_pid == ' + str(pid) for pid in pids)
        switch = ' || '.join(f'prev_pid == {pid} || next_pid == {pid}' for pid in pids)
        filters = {
            'irq/irq_handler_entry': 'irq == ' + str(self.cap['rtc']['irq']),
            'irq/irq_handler_exit': 'irq == ' + str(self.cap['rtc']['irq']),
            'rtc/rtc_set_alarm': 'common_pid == ' + str(self.cap['worker_pid']),
            'rtc/rtc_alarm_irq_enable': 'common_pid == ' + str(self.cap['worker_pid']),
            'sched/sched_switch': switch,
            'lock/contention_begin': chosen, 'lock/contention_end': chosen,
        }
        self.expected_filters = {self.path + '/events/' + name + '/filter': expression for name, expression in filters.items()}
        # A fresh instance must expose the same exact fields as preflight.
        for name in REQUIRED:
            actual = self.io.read(self.path + '/events/' + name + '/format')
            if actual != self.cap['formats'][name]:
                raise ValueError('event format changed: ' + name)
        for name, expression in filters.items():
            path = self.path + '/events/' + name + '/filter'
            self.filters.append(path)  # attempted write may have taken effect
            self.io.write(path, expression)
            if normalized(self.io.read(path)) != normalized(expression):
                raise ValueError('exact filter readback differs: ' + name)
        self.trigger_condition = '(' + prev + ') && prev_state != 0'
        self.trigger_attempted = True
        path = self.path + '/events/sched/sched_switch/trigger'
        self.io.write(path, 'stacktrace:128 if ' + self.trigger_condition)
        actual = [line for line in self.io.read(path).splitlines() if line.strip() and not line.lstrip().startswith('#')]
        self.check_trigger(actual)
        for name in REQUIRED:
            path = self.path + '/events/' + name + '/enable'
            self.enabled.append(path)
            self.io.write(path, '1')
            if self.io.read(path).strip() != '1':
                raise ValueError('event enable readback differs')
        self.anchors = {'monotonic': time.monotonic(), 'boottime': time.clock_gettime(time.CLOCK_BOOTTIME)}
        self.io.write(self.path + '/tracing_on', '1')
        if self.io.read(self.path + '/tracing_on').strip() != '1':
            raise ValueError('trace start readback differs')

    def check_trigger(self, actual):
        if len(actual) != 1:
            raise ValueError('unexpected trigger set')
        match = re.fullmatch(r'stacktrace:count=(\d+) if (.*)', actual[0].strip())
        if not match or not 0 < int(match[1]) <= 128 or normalized(match[2]) != normalized(self.trigger_condition):
            raise ValueError('bounded trigger/filter exhausted or readback differs')

    def ready_to_arm(self):
        """Sync/count waits may consume time or stack budget; recheck before arm."""
        if not self.owned or self.io.read(self.path + '/tracing_on').strip() != '1':
            raise ValueError('owned trace no longer active before alarm arm')
        actual = [line for line in self.io.read(self.path + '/events/sched/sched_switch/trigger').splitlines()
                  if line.strip() and not line.lstrip().startswith('#')]
        self.check_trigger(actual)
        for path in self.enabled:
            if self.io.read(path).strip() != '1':
                raise ValueError('event disabled before alarm arm')
        for path, expression in self.expected_filters.items():
            if normalized(self.io.read(path)) != normalized(expression):
                raise ValueError('exact filter changed before alarm arm')

    def stop(self):
        self.io.write(self.path + '/tracing_on', '0')
        if self.io.read(self.path + '/tracing_on').strip() != '0':
            raise ValueError('trace stop readback differs')
        text = self.io.read(self.path + '/trace')
        self.save_trace(text)
        self.trace_saved = True
        trigger = self.io.read(self.path + '/events/sched/sched_switch/trigger')
        return text, {'clock': self.cap['clock'], 'anchors': self.anchors, 'final_trigger': trigger,
                      'stack_budget_exhausted': 'stacktrace:count=0' in trigger}

    def cleanup(self):
        if not self.owned:
            return None
        errors = []
        def attempt(function):
            try:
                function()
            except Exception as error:
                errors.append({'type': type(error).__name__, 'message': str(error)})
        def reset(path, value, accepted):
            self.io.write(path, value)
            if self.io.read(path).strip() not in accepted:
                raise ValueError('trace cleanup readback differs: ' + path)
        attempt(lambda: reset(self.path + '/tracing_on', '0', {'0'}))
        if not self.trace_saved:
            attempt(lambda: self.save_trace(self.io.read(self.path + '/trace')))
        for path in reversed(self.enabled):
            attempt(lambda path=path: reset(path, '0', {'0'}))
        if self.trigger_attempted:
            # This fresh owned instance contains only our single stack trigger.
            def remove_trigger():
                path = self.path + '/events/sched/sched_switch/trigger'
                self.io.write(path, '!stacktrace')
                if any(line.strip() and not line.lstrip().startswith('#') for line in self.io.read(path).splitlines()):
                    raise ValueError('owned stack trigger still present')
            attempt(remove_trigger)
        for path in reversed(self.filters):
            attempt(lambda path=path: reset(path, '0', {'none', '0'}))
        attempt(lambda: self.io.rmdir(self.path))
        self.owned = False  # no automatic second cleanup attempt
        return {'passed': not errors, 'owned': True, 'errors': errors}


def log_suffix(before, after):
    a, b = before.splitlines(), after.splitlines()
    if not a or not b:
        return {'complete_since_baseline': False, 'overlap_lines': 0, 'new_lines': []}
    matches = []
    for index, line in enumerate(a):
        size = len(a) - index
        if line == b[0] and size <= len(b) and a[index:] == b[:size]:
            matches.append((size, index))
    if not matches:
        return {'complete_since_baseline': False, 'overlap_lines': 0, 'new_lines': []}
    size, dropped = max(matches)
    return {'complete_since_baseline': True, 'overlap_lines': size,
            'old_head_lines_dropped': dropped, 'new_lines': b[size:]}


def analyze(text, primitive, capability, wakeup):
    header = re.search(r'entries-in-buffer/entries-written:\s*(\d+)/(\d+)', text)
    complete = bool(header and header[1] == header[2] and int(header[1]) > 0)
    intervals, open_at, rtc, alarm_sets, alarm_enable = [], None, [], [], []
    for line in text.splitlines():
        m = re.search(r'\s(\d+\.\d+): suspend_resume: machine_suspend\[\d+\] (begin|end)', line)
        if m:
            if m[2] == 'begin':
                open_at = float(m[1])
            elif open_at is not None:
                intervals.append((open_at, float(m[1])))
                open_at = None
        m = re.search(r'\s(\d+\.\d+): irq_handler_entry: irq=(\d+) name=(\S+)', line)
        if m and int(m[2]) == capability['rtc']['irq'] and m[3] == 'pm8xxx_rtc_alarm':
            rtc.append(float(m[1]))
        m = re.search(r'\s(\d+\.\d+): rtc_set_alarm: UTC \((\d+)\) \((-?\d+)\)', line)
        if m:
            alarm_sets.append({'t': float(m[1]), 'target': int(m[2]), 'errno': int(m[3])})
        m = re.search(r'\s(\d+\.\d+): rtc_alarm_irq_enable: (enable|disable) RTC alarm IRQ \((-?\d+)\)', line)
        if m:
            alarm_enable.append({'t': float(m[1]), 'enabled': m[2] == 'enable', 'errno': int(m[3])})
    during = [t for t in rtc if any(start <= t <= end for start, end in intervals)]
    # IRQ timing is a separate fact; absence of a reason register is not zero.
    reason = wakeup.get('available') is True and wakeup.get('value') == capability['rtc']['irq']
    return {'trace_complete': complete, 'machine_suspend_intervals': intervals,
            'RTC_set_alarm_events': alarm_sets, 'RTC_alarm_enable_events': alarm_enable,
            'own_target_set_event_observed': any(row['target'] == primitive.get('alarm_target') and row['errno'] == 0 for row in alarm_sets),
            'RTC_set_event_has_no_device_field': True,
            'rtc_irq_times': rtc, 'rtc_irq_during_machine_suspend_observed': bool(during),
            'reported_wakeup_irq_matches_RTC': bool(complete and during and reason),
            'unique_wakeup_reason': {'proved': False,
                                    'basis': 'first_reported_IRQ_is_not_exclusivity_proof' if reason else 'not_proved',
                                    'reported_irq': wakeup},
            'returned': primitive.get('mem_returned') is True,
            'estimated_residency_seconds': primitive.get('estimated_residency_seconds'),
            'RTC_irq_timing_alone_is_not_unique_cause': True,
            'console_wait_root_cause': 'not_proved; inspect retained targeted stacks/lock events',
            'whole_system_accepted': False}
