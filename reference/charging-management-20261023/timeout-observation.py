"""Observe the actual 36000-second driver timer; never change its clock or limit.

Inert on import. The device adapter owns identity, protection/caps checks, normal
AUTO sysfs requests, bounded CPU load, cancellation and the charging service lock.
No charger register, gauge/protection setting or charging limit is written here.
"""
import errno
import math
import traceback

LIMIT_SECONDS = 36000
TRANSIENT_RETRY_SECONDS = 300
TRANSIENT_RETRY_INTERVAL_SECONDS = 10
TRANSIENT_ERRNOS = frozenset(
    getattr(errno, name)
    for name in ('ENODATA', 'EAGAIN', 'ESTALE', 'ENOLINK', 'ETIMEDOUT')
    if hasattr(errno, name)
)


class RetryableObservationError(RuntimeError):
    """Only explicitly recoverable observation gaps use this exception."""


class ObservationSampleGap(RetryableObservationError):
    pass


class ObservationRetryCancelled(RuntimeError):
    pass


def _is_transient(error):
    return (isinstance(error, RetryableObservationError) or
            isinstance(error, OSError) and
            getattr(error, 'errno', None) in TRANSIENT_ERRNOS)


def observe_timeout(io):
    result = dict(passed=False, timer_limit_seconds=LIMIT_SECONDS,
                  initial_session_seconds=None, initial_boottime=None,
                  timeout_boottime=None, observed_seconds=None,
                  timeout_stop_verified=False, auto_requested_after_timeout=False,
                  timeout_survived_auto=False, load_joined=False,
                  error=None, error_type=None, error_stage=None,
                  error_traceback=None, last_good=None, last_attempt=None,
                  cleanup_error=None, reason=None,
                  transient_events=[], transient_retries=0,
                  retry_exhausted=False, sample_gaps=[],
                  timer_or_charge_parameters_changed=False)
    initial = None
    previous = None
    attempt = None
    stage = 'before'

    def observe(phase):
        nonlocal previous, attempt, stage
        stage = phase
        value = io.observe()
        attempt = dict(phase=phase, value=value)
        # Optional device adapter hook: persist the raw sample before any
        # validation predicate can discard it on failure.
        if hasattr(io, 'attempt'):
            io.attempt(phase, value)
        try:
            io.validate(value)
        except BaseException as error:
            if not getattr(error, 'stage', None):
                error.stage = 'validate:' + phase
            raise
        s = value['sample']
        now = value['boottime']
        if not math.isfinite(now) or now > io.now() or io.now() - now > 3:
            raise RuntimeError('invalid observation timestamp')
        if value['behaviour'] != 'auto':
            raise RuntimeError('requires unchanged AUTO')
        if not 3500000 <= min(s['cell1_uv'], s['cell2_uv']) <= max(
                s['cell1_uv'], s['cell2_uv']) <= 4150000:
            raise RuntimeError('midrange cell observation limit')
        if abs(s['cell1_uv'] - s['cell2_uv']) > 30000 or not 180 <= s['temp_decic'] < 370:
            raise RuntimeError('temperature or imbalance observation limit')
        if s['logical_full'] or s['full_holding'] or s['full_cause']:
            raise RuntimeError('Full boundary changed charge period')
        gap = None
        if previous is not None:
            if now < previous['boottime']:
                raise RuntimeError('observation clock rollback')
            if now - previous['boottime'] > 30:
                gap = dict(phase=phase, previous_boottime=previous['boottime'],
                           boottime=now, gap_seconds=now - previous['boottime'])
            elif s['session_seconds'] < previous['sample']['session_seconds']:
                raise RuntimeError('driver timer reset')
        if initial is not None:
            elapsed = now - initial['boottime']
            expected = min(LIMIT_SECONDS, initial['sample']['session_seconds'] + elapsed)
            if abs(s['session_seconds'] - expected) > 3:
                raise RuntimeError('driver counter disagrees with actual BOOTTIME')
        if s['cycle_timeout']:
            if initial is None or s['session_seconds'] != LIMIT_SECONDS:
                raise RuntimeError('timeout was already present or counter is invalid')
            if (now - initial['boottime'] < LIMIT_SECONDS - initial['sample']['session_seconds'] - 2 or
                    s['latched'] != 1 or s['error'] != -62 or s['stop_error'] != 0 or
                    s['desired_enable'] != 0 or value['register08'] & 0x18 != 8):
                raise RuntimeError('timeout timing or actual stop not confirmed')
        elif (s['latched'] or s['error'] or s['stop_error'] or s['desired_enable'] != 1 or
                value['register08'] & 0x18 != 0x10):
            raise RuntimeError('charging stopped before the expected timeout')
        if gap is not None:
            result['sample_gaps'].append(gap)
            # Anchor the next retry to this fully validated fresh sample. The
            # gap is still recorded and this sample is not marked good.
            previous = value
            error = ObservationSampleGap('observation sample gap')
            error.stage = 'sample_gap:' + phase
            raise error
        io.record(phase, value)
        previous = value
        result['last_good'] = value
        attempt = None
        return value

    def observe_with_retry(phase):
        retry_started = None
        while True:
            try:
                return observe(phase)
            except BaseException as error:
                if not _is_transient(error):
                    raise
                now = io.now()
                if retry_started is None:
                    retry_started = now
                code = getattr(error, 'errno', None)
                event = dict(
                    phase=phase, boottime=now, error=repr(error),
                    error_type=type(error).__name__, errno=code,
                    errno_name=errno.errorcode.get(code),
                    traceback=traceback.format_exc())
                result['transient_events'].append(event)
                result['transient_retries'] += 1
                if hasattr(io, 'retry'):
                    io.retry(phase, error, event)
                remaining = TRANSIENT_RETRY_SECONDS - (now - retry_started)
                if remaining <= 0:
                    result['retry_exhausted'] = True
                    error.retry_exhausted = True
                    if hasattr(io, 'retry_exhausted'):
                        io.retry_exhausted(phase, error, result['transient_events'])
                    raise
                if io.cancelled():
                    raise ObservationRetryCancelled(
                        'cancelled during transient observation retry') from error
                io.sleep(min(TRANSIENT_RETRY_INTERVAL_SECONDS, remaining))

    try:
        initial = observe_with_retry('before')
        seconds = initial['sample']['session_seconds']
        if type(seconds) is not int or not 0 <= seconds <= 900:
            raise RuntimeError('requires a recent healthy charge period')
        result.update(initial_session_seconds=seconds, initial_boottime=initial['boottime'])
        deadline = initial['boottime'] + LIMIT_SECONDS - seconds + 120
        while True:
            value = observe_with_retry('timing')
            if value['sample']['cycle_timeout']:
                result.update(timeout_boottime=value['boottime'],
                              observed_seconds=value['boottime'] - initial['boottime'])
                break
            if io.cancelled():
                result['reason'] = 'cancelled'
                return result
            if io.now() >= deadline:
                result['reason'] = 'deadline_without_timeout'
                return result
            io.balance(value)
            io.sleep(min(10, deadline - io.now()))
        # Remove only the experiment's CPU load. The actual timeout stays latched.
        io.stop_load()
        io.sleep(5)
        stopped = observe_with_retry('stopped')
        if stopped['boottime'] <= value['boottime']:
            raise RuntimeError('timeout recheck is not a fresh sample')
        if stopped['sample']['cycle_timeout'] != 1:
            raise RuntimeError('timeout recheck did not retain cycle_timeout')
        result['timeout_stop_verified'] = True
        if io.cancelled():
            result['reason'] = 'cancelled_after_timeout'
            return result
        io.request_auto()
        result['auto_requested_after_timeout'] = True
        # AUTO clears the independent operator latch but the next actual safety
        # poll must retain cycle_timeout and keep CHG stopped. Do not use the
        # management command that expects a fault-free resume and would inhibit
        # on this intentionally expired period.
        io.sleep(3)
        for number in range(4):
            if io.cancelled():
                result['reason'] = 'cancelled_after_AUTO'
                return result
            value = observe_with_retry('after_auto')
            if not value['sample']['cycle_timeout']:
                raise RuntimeError('AUTO erased the established timeout')
            if number < 3:
                io.sleep(10)
        result.update(timeout_survived_auto=True, reason='actual_timeout_and_AUTO_hold')
    except ObservationRetryCancelled as error:
        result['reason'] = 'cancelled_during_retry'
        result['retry_cancelled_error'] = repr(error.__cause__)
    except BaseException as error:
        result.update(error=repr(error), error_type=type(error).__name__,
                      error_stage=getattr(error, 'stage', stage),
                      error_traceback=traceback.format_exc(),
                      last_attempt=attempt)
    finally:
        try:
            io.stop_load()
            result['load_joined'] = True
        except BaseException as error:
            result['cleanup_error'] = repr(error)
    result['passed'] = bool(result['timeout_stop_verified'] and result['timeout_survived_auto'] and
                            result['load_joined'] and result['error'] is None and
                            result['cleanup_error'] is None)
    return result
