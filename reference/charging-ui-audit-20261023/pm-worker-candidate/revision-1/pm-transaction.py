"""One RTC-backed PM transaction, with injectable OS boundaries.

This module does nothing on import. A caller must own the phone/RTC window and
perform its normal boot/driver/manifest checks before calling suspend_once().
The return value proves transaction ordering, never whole-device PM acceptance.
"""
from pathlib import Path
import errno
import math
import os
import subprocess
import sys
import time


class PreparationAborted(RuntimeError):
    pass


def suspend_once(io, *, alarm_delay_seconds=15, minimum_remaining_seconds=4,
                 wakeup_count_timeout_seconds=10):
    """Perform at most one mem write; never retry or replace another alarm.

    The count must be read BEFORE arming: read may wait for in-progress events
    to drain. Reading after arming could absorb this transaction's expired RTC
    event into the saved count, allowing a later sleep without a future alarm.

    io supplies clocks, phase logging, RTC/IRQ/count access, sync and one-shot
    writes. In-progress wakeup_count waits are bounded by the real OS adapter.
    A sync can block, but it runs before this transaction creates any alarm.
    """
    if (type(alarm_delay_seconds) is not int or type(minimum_remaining_seconds) is not int
            or not 1 <= minimum_remaining_seconds < alarm_delay_seconds - 1
            or type(wakeup_count_timeout_seconds) not in [int, float]
            or not math.isfinite(wakeup_count_timeout_seconds)
            or wakeup_count_timeout_seconds <= 0):
        raise ValueError('invalid alarm/remaining/count timeout configuration')
    result = {'outcome': 'preparing', 'mem_write_attempts': 0, 'mem_returned': False,
              'alarm_target': None, 'phases': [], 'cleanup': 'not_owned',
              'whole_device_pm_acceptance': False}
    owned_target = None

    def phase(name, **fields):
        entry = {'phase': name, 'monotonic': io.monotonic(), **fields}
        result['phases'].append(entry)
        io.phase(entry)

    try:
        phase('preflight')
        if io.read_alarm() is not None:
            raise PreparationAborted('RTC alarm already owned by another operation')
        phase('sync_begin')
        sync_start = io.monotonic()
        io.sync()
        result['sync_seconds'] = io.monotonic() - sync_start
        phase('sync_complete', elapsed_seconds=result['sync_seconds'])
        # No RTC alarm from this operation exists during this potentially
        # blocking read. Its snapshot is kept unchanged for the handshake.
        phase('wakeup_count_read_begin')
        count_start = io.monotonic()
        saved_count = io.read_wakeup_count(wakeup_count_timeout_seconds)
        if type(saved_count) is not int or saved_count < 0:
            raise ValueError('invalid wakeup_count')
        result['saved_wakeup_count'] = saved_count
        result['wakeup_count_read_seconds'] = io.monotonic() - count_start
        phase('wakeup_count_read_complete', elapsed_seconds=result['wakeup_count_read_seconds'])
        # Recheck after sync/count wait. The caller coordinates exclusive RTC
        # use; these checks also avoid clobbering a known changed owner.
        if io.read_alarm() is not None:
            raise PreparationAborted('RTC alarm changed before arm')
        initial_irq = io.read_rtc_irq()
        target = io.read_rtc_epoch() + alarm_delay_seconds
        result['alarm_target'] = target
        # Set tentative ownership BEFORE the write. A failed/short write may
        # still have installed the target, which must be cleaned up safely.
        owned_target = target
        io.write_alarm(target)
        if io.read_alarm() != target:
            raise PreparationAborted('RTC alarm readback does not match target')
        phase('alarm_armed', target=target, requested_delay_seconds=alarm_delay_seconds)
        # Logging can block, so emit the entering marker BEFORE the final
        # checks/handshake. No logging or other slow work separates the
        # accepted count write from the single mem write.
        phase('entering_mem', target=target)
        alarm_now = io.read_alarm()
        rtc_now = io.read_rtc_epoch()
        irq_now = io.read_rtc_irq()
        # since_epoch is integer seconds; subtract one for its quantization.
        remaining_lower_bound = target - rtc_now - 1
        result['pre_mem'] = {'rtc_epoch': rtc_now, 'alarm': alarm_now,
                             'remaining_lower_bound_seconds': remaining_lower_bound,
                             'rtc_irq_delta': irq_now - initial_irq}
        if alarm_now != target:
            raise PreparationAborted('RTC alarm consumed or replaced before mem')
        if remaining_lower_bound < minimum_remaining_seconds:
            raise PreparationAborted('insufficient RTC time remaining before mem')
        if irq_now != initial_irq:
            raise PreparationAborted('RTC interrupt already occurred before mem')
        io.write_wakeup_count(saved_count)
        # Any event after the accepted handshake remains visible to the
        # kernel's pm_wakeup_pending check; do not read a new count here.
        mono = io.monotonic()
        boottime = io.boottime()
        result['mem_write_attempts'] = 1
        io.suspend_to_mem()
        result['mem_returned'] = True
        result['monotonic_seconds'] = io.monotonic() - mono
        result['boottime_seconds'] = io.boottime() - boottime
        result['estimated_residency_seconds'] = result['boottime_seconds'] - result['monotonic_seconds']
        result['outcome'] = 'returned'
        phase('returned_from_mem')
    except Exception as error:
        result['outcome'] = 'aborted' if not result['mem_write_attempts'] else 'failed'
        result['error'] = {'type': type(error).__name__, 'message': str(error),
                           'errno': getattr(error, 'errno', None)}
        try:
            phase(result['outcome'], error_type=type(error).__name__)
        except Exception as logging_error:
            result['phase_logging_error'] = str(logging_error)
    finally:
        if owned_target is not None:
            try:
                current = io.read_alarm()
                if current == owned_target:
                    io.write_alarm(0)
                    if io.read_alarm() is not None:
                        raise OSError(errno.EIO, 'owned alarm did not clear')
                    result['cleanup'] = 'owned_alarm_cancelled'
                elif current is None:
                    result['cleanup'] = 'alarm_already_consumed_or_cleared'
                else:
                    result['cleanup'] = 'changed_alarm_preserved'
            except Exception as error:
                result['cleanup'] = 'unknown_or_failed'
                result['cleanup_error'] = {'type': type(error).__name__, 'message': str(error),
                                           'errno': getattr(error, 'errno', None)}
                if result['outcome'] == 'returned':
                    result['outcome'] = 'failed'
    return result


class SysfsPMIO:
    """Linux-only OS adapter; no operation occurs merely by constructing it."""
    def __init__(self, phase_logger, *, rtc='/sys/class/rtc/rtc0', power='/sys/power',
                 interrupts='/proc/interrupts'):
        self.rtc = Path(rtc)
        self.power = Path(power)
        self.interrupts = Path(interrupts)
        self.phase_logger = phase_logger

    @staticmethod
    def _single_write(path, payload):
        """One sysfs write syscall; never retry a short write with a new chunk."""
        fd = os.open(path, os.O_WRONLY | os.O_CLOEXEC)
        try:
            written = os.write(fd, payload)
            if written != len(payload):
                raise OSError(errno.EIO, 'short sysfs write')
        finally:
            os.close(fd)

    @staticmethod
    def _number(text, label):
        text = text.strip()
        if not text.isascii() or not text.isdigit():
            raise ValueError('invalid ' + label)
        return int(text)

    def phase(self, entry):
        self.phase_logger(entry)

    def monotonic(self):
        return time.monotonic()

    def boottime(self):
        return time.clock_gettime(time.CLOCK_BOOTTIME)

    def sync(self):
        os.sync()

    def read_alarm(self):
        text = (self.rtc / 'wakealarm').read_text().strip()
        if text in ['', '0']:
            return None
        return self._number(text, 'wakealarm')

    def read_rtc_epoch(self):
        return self._number((self.rtc / 'since_epoch').read_text(), 'RTC epoch')

    def read_rtc_irq(self):
        rows = [row for row in self.interrupts.read_text().splitlines()
                if row.rstrip().endswith('pm8xxx_rtc_alarm')]
        if len(rows) != 1:
            raise ValueError('RTC interrupt identity is missing or ambiguous')
        # CPU count is derived from the numeric prefix, not fixed at eight.
        fields = rows[0].split(':', 1)[1].split()
        counts = []
        for value in fields:
            if not value.isascii() or not value.isdigit():
                break
            counts.append(int(value))
        if not counts:
            raise ValueError('RTC interrupt counters missing')
        return sum(counts)

    def read_wakeup_count(self, timeout):
        # The kernel's sysfs show waits interruptibly for in_progress == 0;
        # O_NONBLOCK does not bound that wait. A disposable child can be
        # terminated on timeout, unlike a Python thread blocked in os.read.
        code = ('import os,sys\n'
                'fd=os.open(sys.argv[1],os.O_RDONLY|os.O_CLOEXEC)\n'
                'try: data=os.read(fd,128)\n'
                'finally: os.close(fd)\n'
                'sys.stdout.buffer.write(data)\n')
        try:
            response = subprocess.run([sys.executable, '-c', code, str(self.power / 'wakeup_count')],
                                      stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            raise TimeoutError(errno.ETIMEDOUT, 'wakeup_count wait timed out before RTC arm') from error
        if response.returncode:
            raise OSError(errno.EIO, 'wakeup_count reader failed')
        return self._number(response.stdout.decode('ascii'), 'wakeup_count')

    def write_alarm(self, target):
        self._single_write(self.rtc / 'wakealarm', str(target).encode('ascii'))

    def write_wakeup_count(self, count):
        self._single_write(self.power / 'wakeup_count', str(count).encode('ascii'))

    def suspend_to_mem(self):
        self._single_write(self.power / 'state', b'mem')
